"""
Legal Sources — OpenLegi MCP Fetcher

Fetcher alternatif utilisant le serveur MCP OpenLegi (mcp.openlegi.fr)
pour accéder aux données Légifrance sans credentials PISTE.

Ce fetcher communique avec le serveur MCP via JSON-RPC over HTTP
et parse les réponses textuelles en LegalDoc structurés.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import LegalSourcesConfig, PRIORITY_CODES
from ..models import (
    AccessMode,
    DocumentType,
    Jurisdiction,
    LegalDoc,
    LegalSource,
    Provenance,
    create_compliant_provenance,
)

logger = logging.getLogger("legal_sources.openlegi")


# --------------------------------------------------------------------------- #
# Search queries per code – broad enough to capture most contract-relevant
# articles while avoiding overwhelming the API.
# --------------------------------------------------------------------------- #
CODE_SEARCH_QUERIES: Dict[str, List[str]] = {
    "Code civil": [
        "contrat",
        "obligation",
        "responsabilité",
        "vente",
        "propriété",
        "bail",
        "mandat",
        "garantie",
        "dommage",
        "préjudice",
        "résolution",
        "résiliation",
        "clause",
        "consentement",
        "nullité",
        "prescription",
        "paiement",
        "dette",
        "cession",
        "subrogation",
    ],
    "Code de commerce": [
        "commercial",
        "société",
        "concurrence",
        "fonds",
        "bail",
        "contrat",
        "créance",
        "procédure collective",
        "liquidation",
        "sauvegarde",
        "redressement",
        "acte",
        "registre",
        "délai",
        "paiement",
    ],
    "Code de la propriété intellectuelle": [
        "brevet",
        "marque",
        "droit d'auteur",
        "licence",
        "contrefaçon",
        "oeuvre",
        "reproduction",
        "exploitation",
        "cession",
        "logiciel",
        "base de données",
        "dessin",
        "modèle",
    ],
    "Code du travail": [
        "contrat de travail",
        "licenciement",
        "salaire",
        "durée",
        "congé",
        "rupture",
        "indemnité",
        "non-concurrence",
        "confidentialité",
        "clause",
        "période d'essai",
        "préavis",
    ],
    "Code de la consommation": [
        "consommateur",
        "garantie",
        "clause abusive",
        "pratique commerciale",
        "information",
        "rétractation",
        "délai",
        "contrat",
        "conformité",
        "réparation",
    ],
    "Code pénal": [
        "abus de confiance",
        "escroquerie",
        "contrefaçon",
        "atteinte",
        "secret",
        "recel",
        "corruption",
        "données",
    ],
    "Code de procédure civile": [
        "compétence",
        "assignation",
        "jugement",
        "appel",
        "exécution",
        "référé",
        "mesure conservatoire",
        "arbitrage",
    ],
    "Code général des impôts": [
        "TVA",
        "impôt",
        "société",
        "plus-value",
        "déduction",
        "bénéfice",
    ],
}


class OpenLegiMCPClient:
    """
    Client MCP minimal pour le serveur OpenLegi.

    Gère l'initialisation de session, les appels d'outils,
    le rate limiting et le renouvellement de session.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url
        self.token = token
        self.timeout = timeout
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._http = self._make_session()

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}?token={self.token}"

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    # ---- low-level -------------------------------------------------------- #

    def _post(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and return the parsed result."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        for retry in range(4):
            resp = self._http.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            # Handle rate limiting with exponential backoff
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 15))
                wait = max(retry_after, 5 * (retry + 1))
                logger.warning(
                    "Rate limited (429). Waiting %ds before retry %d/3…",
                    wait,
                    retry + 1,
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            break
        else:
            raise RuntimeError("Rate limited after 4 retries")

        # Extract session id from headers (set on initialize)
        if "mcp-session-id" in resp.headers:
            self._session_id = resp.headers["mcp-session-id"]

        # Force UTF-8 decoding (SSE text/event-stream doesn't set charset,
        # causing requests to default to Latin-1 and garble accented chars).
        text = resp.content.decode("utf-8").strip()
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                raw = line[len("data:"):].strip()
                return json.loads(raw)

        # Fallback: try direct JSON parse
        return json.loads(text)

    # ---- high-level ------------------------------------------------------- #

    def initialize(self) -> Dict[str, Any]:
        """Initialize MCP session."""
        result = self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "korev-ingest", "version": "1.0"},
        })
        logger.info(
            "MCP session initialized: server=%s",
            result.get("result", {}).get("serverInfo", {}).get("name", "?"),
        )
        return result

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Call an MCP tool and return its text content.

        Re-initializes the session on failure (session expired).
        """
        for attempt in range(2):
            try:
                result = self._post("tools/call", {
                    "name": name,
                    "arguments": arguments,
                })

                # Check for errors
                if "error" in result:
                    err = result["error"]
                    if "session" in str(err).lower() and attempt == 0:
                        logger.warning("Session expired, re-initializing…")
                        self._session_id = None
                        self.initialize()
                        continue
                    raise RuntimeError(f"MCP error: {err}")

                # Extract text content
                content_list = result.get("result", {}).get("content", [])
                texts = [c["text"] for c in content_list if c.get("type") == "text"]
                return "\n".join(texts)

            except requests.exceptions.RequestException as exc:
                if attempt == 0:
                    logger.warning("Request failed (%s), retrying…", exc)
                    time.sleep(2)
                    self._session_id = None
                    self.initialize()
                    continue
                raise

        return ""


# --------------------------------------------------------------------------- #
# Article parser — extracts structured data from MCP text responses
# --------------------------------------------------------------------------- #

_ARTICLE_BLOCK_RE = re.compile(
    r"=== ARTICLE CODE \d+ ===\s*\n(.*?)(?==== ARTICLE CODE|\Z)",
    re.DOTALL,
)

_FIELD_RE = {
    "origin_id": re.compile(r"Identifiant article:\s*(\S+)"),
    "cid": re.compile(r"CID article:\s*(\S+)"),
    "article_num": re.compile(r"[Nn]um[ée]ro article:\s*(\S+)"),
    "status": re.compile(r"[ÉEe]tat juridique:\s*(\S+)"),
    "date_debut": re.compile(r"Date d[ée]but vigueur:\s*([\d/]+)"),
    "date_fin": re.compile(r"Date fin vigueur:\s*([\d/]+)"),
    "link": re.compile(r"Lien article L[ée]gifrance:\s*(https://\S+)"),
    "section": re.compile(r"Section parente:\s*(.+)"),
    "path": re.compile(r"Chemin complet:\s*(.+)"),
}

# Fallback: extract article number from header line "Article XXXX - (VIGUEUR)"
_ARTICLE_HEADER_RE = re.compile(r"^Article\s+([\w./-]+)\s*-", re.MULTILINE)


def _extract_content(block: str) -> str:
    """Extract the article text from a CONTENU: section."""
    m = re.search(r"CONTENU:\s*\n(?:Texte de l'article:\s*\n)?(.*?)(?:\nARTICLES CITÉS:|\Z)", block, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Fallback — everything after CONTENU:
    m2 = re.search(r"CONTENU:\s*\n(.*)", block, re.DOTALL)
    return m2.group(1).strip() if m2 else ""


def parse_mcp_response(text: str) -> List[Dict[str, str]]:
    """
    Parse the formatted text returned by rechercher_code into a list of
    article dicts with keys: origin_id, cid, article_num, status,
    date_debut, link, section, text.
    """
    articles: List[Dict[str, str]] = []

    for match in _ARTICLE_BLOCK_RE.finditer(text):
        block = match.group(1)
        article: Dict[str, str] = {}

        for key, pattern in _FIELD_RE.items():
            m = pattern.search(block)
            if m:
                article[key] = m.group(1).strip()

        article["text"] = _extract_content(block)

        # Fallback: extract article_num from header line if field regex missed
        if not article.get("article_num"):
            hm = _ARTICLE_HEADER_RE.search(block)
            if hm:
                article["article_num"] = hm.group(1)

        # Only keep articles that are in force and have content
        if article.get("origin_id") and article.get("text"):
            articles.append(article)

    return articles


# --------------------------------------------------------------------------- #
# Code abbreviations (reused from legifrance.py)
# --------------------------------------------------------------------------- #
CODE_ABBREV = {
    "Code civil": "C. civ.",
    "Code pénal": "C. pén.",
    "Code de commerce": "C. com.",
    "Code du travail": "C. trav.",
    "Code de procédure civile": "C. pr. civ.",
    "Code de procédure pénale": "C. pr. pén.",
    "Code général des impôts": "CGI",
    "Code de la consommation": "C. consom.",
    "Code de la propriété intellectuelle": "CPI",
    "Code de l'environnement": "C. envir.",
}


# --------------------------------------------------------------------------- #
# OpenLegi Fetcher
# --------------------------------------------------------------------------- #

class OpenLegiFetcher:
    """
    Fetcher qui utilise le serveur MCP OpenLegi pour récupérer
    les articles de codes français et les convertir en LegalDoc.

    Ne nécessite PAS de credentials PISTE.
    """

    source = LegalSource.LEGI

    def __init__(
        self,
        token: str,
        config: Optional[LegalSourcesConfig] = None,
        base_url: str = "https://mcp.openlegi.fr/legifrance/mcp",
    ):
        self.config = config or LegalSourcesConfig()
        self.client = OpenLegiMCPClient(base_url, token, timeout=45)
        self._seen_origin_ids: set = set()

    def _build_citation(self, code_name: str, article_num: str) -> str:
        abbrev = CODE_ABBREV.get(code_name, code_name[:15])
        if article_num:
            return f"Art. {article_num} {abbrev}"
        return abbrev

    def _parse_date_fr(self, date_str: str) -> Optional[datetime]:
        """Parse dd/mm/yyyy format."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            return None

    def _article_to_legal_doc(
        self,
        article: Dict[str, str],
        code_name: str,
    ) -> Optional[LegalDoc]:
        """Convert a parsed article dict into a LegalDoc."""
        origin_id = article.get("origin_id", "")
        text = article.get("text", "")
        article_num = article.get("article_num", "")

        if not origin_id or not text:
            return None

        # Dedup
        if origin_id in self._seen_origin_ids:
            return None
        self._seen_origin_ids.add(origin_id)

        citation = self._build_citation(code_name, article_num)
        origin_url = article.get("link", f"https://www.legifrance.gouv.fr/codes/article_lc/{article.get('cid', origin_id)}")

        content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]

        provenance = create_compliant_provenance(
            source=LegalSource.LEGI,
            origin_id=origin_id,
            origin_url=origin_url,
            content_hash=content_hash,
        )
        # Override terms for OpenLegi access path
        provenance.api_version = "openlegi-mcp-1.26"
        provenance.terms_name = "CGU PISTE (via OpenLegi MCP gateway)"

        date = self._parse_date_fr(article.get("date_debut", ""))
        title = f"Article {article_num}" if article_num else f"Article {origin_id}"
        section = article.get("section", "")
        if section:
            title = f"{title} - {section}"

        doc = LegalDoc(
            doc_id="",  # auto-computed
            source=LegalSource.LEGI,
            origin_id=origin_id,
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title=title,
            citation=citation,
            date=date,
            text=text,
            code_name=code_name,
            article_number=article_num,
            provenance=provenance,
            content_hash=content_hash,
        )
        return doc

    def fetch_code(
        self,
        code_name: str,
        queries: Optional[List[str]] = None,
        max_pages: int = 5,
        page_size: int = 10,
    ) -> Generator[LegalDoc, None, None]:
        """
        Fetch articles from a single code using multiple search queries.

        Args:
            code_name: Full code name (e.g. "Code civil")
            queries: Search terms. Defaults to CODE_SEARCH_QUERIES.
            max_pages: Max pages per query (paginating 10 results at a time)
            page_size: Results per page (max 10 for shared credentials)

        Yields:
            LegalDoc for each unique article found.
        """
        queries = queries or CODE_SEARCH_QUERIES.get(code_name, ["contrat"])

        for query in queries:
            logger.info("[%s] Searching: %s", code_name, query)

            for page in range(1, max_pages + 1):
                try:
                    raw = self.client.call_tool("rechercher_code", {
                        "search": query,
                        "code_name": code_name,
                        "champ": "ALL",
                        "page_number": page,
                        "page_size": page_size,
                    })
                except Exception as exc:
                    logger.error("[%s] query=%s page=%d error: %s", code_name, query, page, exc)
                    break

                # Detect MCP-level error messages in the tool response
                if raw.startswith("Error executing tool"):
                    logger.warning("[%s] query=%s: %s", code_name, query, raw[:200])
                    break

                articles = parse_mcp_response(raw)
                logger.debug(
                    "[%s] query=%s page=%d → articles=%d",
                    code_name, query, page, len(articles),
                )

                if not articles:
                    break  # No more results

                for art in articles:
                    doc = self._article_to_legal_doc(art, code_name)
                    if doc:
                        yield doc

                # Check if there are more pages
                if f"Page {page}/" in raw:
                    # Extract total pages
                    m = re.search(r"Page\s+(\d+)/(\d+)", raw)
                    if m and int(m.group(1)) >= int(m.group(2)):
                        break  # Last page
                else:
                    break  # No pagination info → single page

                # Respect rate limits (50 req/min for shared credentials)
                time.sleep(1.5)

    def fetch_all(
        self,
        codes: Optional[List[str]] = None,
        limit: Optional[int] = None,
        max_pages_per_query: int = 5,
    ) -> Generator[LegalDoc, None, None]:
        """
        Fetch articles from all priority codes.

        Args:
            codes: Codes to fetch (defaults to PRIORITY_CODES)
            limit: Global max articles
            max_pages_per_query: Pages per search query

        Yields:
            LegalDoc for each unique article
        """
        codes = codes or PRIORITY_CODES
        total = 0

        for code_name in codes:
            logger.info("=== Fetching %s ===", code_name)

            for doc in self.fetch_code(
                code_name,
                max_pages=max_pages_per_query,
            ):
                yield doc
                total += 1

                if limit and total >= limit:
                    logger.info("Global limit reached: %d", total)
                    return

            logger.info(
                "Completed %s — total unique articles so far: %d",
                code_name,
                total,
            )


# --------------------------------------------------------------------------- #
# Convenience: run ingestion into FTS5 index
# --------------------------------------------------------------------------- #

def run_openlegi_ingestion(
    token: str,
    config: Optional[LegalSourcesConfig] = None,
    codes: Optional[List[str]] = None,
    limit: Optional[int] = None,
    max_pages: int = 5,
) -> Dict[str, Any]:
    """
    End-to-end ingestion from OpenLegi → FTS5 index.

    Returns:
        Stats dict with counts.
    """
    from ..indexing import LegalIndex
    from ..chunking import LegalChunker, ChunkerConfig
    from ..models import IngestionResult

    cfg = config or LegalSourcesConfig()
    cfg.ensure_dirs()

    index = LegalIndex(cfg.index_dir)
    chunker = LegalChunker(ChunkerConfig(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    ))

    result = IngestionResult(source=LegalSource.LEGI, started_at=datetime.utcnow())

    fetcher = OpenLegiFetcher(token=token, config=cfg)

    # Initialize MCP session
    fetcher.client.initialize()

    for doc in fetcher.fetch_all(codes=codes, limit=limit, max_pages_per_query=max_pages):
        result.docs_fetched += 1

        # Validate provenance
        try:
            doc.validate_for_indexing()
        except Exception as exc:
            logger.warning("Provenance rejected: %s", exc)
            result.docs_rejected_no_provenance += 1
            continue

        result.docs_parsed += 1

        # Idempotence
        if index.doc_exists(doc.doc_id):
            result.docs_skipped += 1
            continue

        # Store processed file
        doc_path = cfg.processed_dir / "legi" / f"{doc.doc_id}.json"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        with open(doc_path, "w", encoding="utf-8") as f:
            json.dump(doc.to_dict(), f, ensure_ascii=False, indent=2)

        # Index doc
        index.add_doc(doc)
        result.docs_indexed += 1

        # Chunk and index
        for chunk in chunker.chunk_document(doc):
            if not index.chunk_exists(chunk.chunk_id):
                index.add_chunk(chunk)
                result.chunks_created += 1

        result.last_doc_id = doc.doc_id

        if result.docs_indexed % 25 == 0:
            logger.info(
                "Progress: indexed=%d  chunks=%d  skipped=%d",
                result.docs_indexed,
                result.chunks_created,
                result.docs_skipped,
            )

    result.completed_at = datetime.utcnow()

    stats = {
        **result.to_dict(),
        "index_stats": index.get_stats(),
    }

    logger.info(
        "Ingestion complete: indexed=%d  chunks=%d  duration=%.1fs",
        result.docs_indexed,
        result.chunks_created,
        result.duration_seconds,
    )

    # Save report
    report_path = cfg.base_dir / "reports" / f"ingest_openlegi_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(stats, f, indent=2)

    return stats
