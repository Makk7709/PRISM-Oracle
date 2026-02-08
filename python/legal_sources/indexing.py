"""
Legal Sources — SQLite FTS5 Index

Index lexical + metadata pour recherche et lookup.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from .models import LegalChunk, LegalDoc, LegalSource, Provenance

logger = logging.getLogger("legal_sources.indexing")


@dataclass
class SearchResult:
    """Résultat de recherche."""
    chunk_id: str
    doc_id: str
    source: str
    citation: str
    pinpoint: str
    text_snippet: str
    score: float
    provenance: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source": self.source,
            "citation": self.citation,
            "pinpoint": self.pinpoint,
            "text_snippet": self.text_snippet,
            "score": self.score,
            "provenance": self.provenance,
        }


class LegalIndex:
    """
    Index SQLite avec FTS5 pour recherche plein texte.
    
    Tables:
    - docs: Documents juridiques (métadonnées)
    - chunks: Chunks indexables
    - fts_chunks: Table FTS5 pour recherche plein texte
    
    Usage:
        index = LegalIndex(Path("data/legal/index"))
        index.add_chunk(chunk)
        results = index.search("L132-8", source="legi", limit=10)
    """
    
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = index_dir / "legal_index.sqlite"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialise le schéma de la base."""
        with self._get_conn() as conn:
            # Table docs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS docs (
                    doc_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    origin_id TEXT NOT NULL,
                    document_type TEXT,
                    jurisdiction TEXT,
                    title TEXT,
                    citation TEXT,
                    date TEXT,
                    code_name TEXT,
                    article_number TEXT,
                    court TEXT,
                    chamber TEXT,
                    decision_number TEXT,
                    ecli TEXT,
                    content_hash TEXT,
                    provenance_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, origin_id)
                )
            """)
            
            # Table chunks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER,
                    source TEXT NOT NULL,
                    document_type TEXT,
                    citation TEXT,
                    pinpoint TEXT,
                    text TEXT,
                    provenance_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES docs(doc_id)
                )
            """)
            
            # Table FTS5 pour recherche plein texte
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                    chunk_id,
                    text,
                    citation,
                    pinpoint,
                    content='chunks',
                    content_rowid='rowid'
                )
            """)
            
            # Triggers pour maintenir FTS5 synchronisé
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO fts_chunks(rowid, chunk_id, text, citation, pinpoint)
                    VALUES (new.rowid, new.chunk_id, new.text, new.citation, new.pinpoint);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO fts_chunks(fts_chunks, rowid, chunk_id, text, citation, pinpoint)
                    VALUES ('delete', old.rowid, old.chunk_id, old.text, old.citation, old.pinpoint);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO fts_chunks(fts_chunks, rowid, chunk_id, text, citation, pinpoint)
                    VALUES ('delete', old.rowid, old.chunk_id, old.text, old.citation, old.pinpoint);
                    INSERT INTO fts_chunks(rowid, chunk_id, text, citation, pinpoint)
                    VALUES (new.rowid, new.chunk_id, new.text, new.citation, new.pinpoint);
                END
            """)
            
            # Index pour lookups rapides
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_source ON docs(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_origin_id ON docs(origin_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")
            
            conn.commit()
        
        logger.info(f"Initialized legal index at {self.db_path}")
    
    @contextmanager
    def _get_conn(self):
        """Context manager pour connexion SQLite."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        try:
            yield conn
        finally:
            conn.close()
    
    def add_doc(self, doc: LegalDoc) -> bool:
        """
        Ajoute un document à l'index.
        
        Returns:
            True si ajouté, False si déjà existant (idempotent)
        """
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO docs (
                        doc_id, source, origin_id, document_type, jurisdiction,
                        title, citation, date, code_name, article_number,
                        court, chamber, decision_number, ecli, content_hash,
                        provenance_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc.doc_id,
                    doc.source.value,
                    doc.origin_id,
                    doc.document_type.value,
                    doc.jurisdiction.value,
                    doc.title,
                    doc.citation,
                    doc.date.isoformat() if doc.date else None,
                    doc.code_name,
                    doc.article_number,
                    doc.court,
                    doc.chamber,
                    doc.decision_number,
                    doc.ecli,
                    doc.content_hash,
                    json.dumps(doc.provenance.to_dict()) if doc.provenance else None,
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def add_chunk(self, chunk: LegalChunk) -> bool:
        """
        Ajoute un chunk à l'index.
        
        Returns:
            True si ajouté, False si déjà existant
        """
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO chunks (
                        chunk_id, doc_id, chunk_index, source, document_type,
                        citation, pinpoint, text, provenance_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk.chunk_id,
                    chunk.doc_id,
                    chunk.chunk_index,
                    chunk.source.value,
                    chunk.document_type.value,
                    chunk.citation,
                    chunk.pinpoint,
                    chunk.text,
                    json.dumps(chunk.provenance.to_dict()),
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def _escape_fts_query(self, query: str) -> str:
        """
        Échappe une requête pour FTS5.
        
        Les caractères spéciaux comme - sont traités comme des opérateurs.
        On wrappe chaque terme entre guillemets pour une recherche littérale.
        """
        # Split en termes
        terms = query.strip().split()
        
        # Échapper chaque terme
        escaped_terms = []
        for term in terms:
            # Si contient des caractères spéciaux, wrapper en guillemets
            if any(c in term for c in '-+*"\'()'):
                escaped_terms.append(f'"{term}"')
            else:
                escaped_terms.append(term)
        
        return " ".join(escaped_terms)
    
    def search(
        self,
        query: str,
        source: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Recherche plein texte dans les chunks.
        
        Args:
            query: Termes de recherche
            source: Filtrer par source (legi, cass, etc.)
            limit: Nombre max de résultats
            
        Returns:
            Liste de SearchResult triés par pertinence
        """
        results = []
        
        # Escape query for FTS5 (wrap each term in quotes)
        escaped_query = self._escape_fts_query(query)
        
        with self._get_conn() as conn:
            # Construire la requête FTS5
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.source,
                    c.citation,
                    c.pinpoint,
                    c.text,
                    c.provenance_json,
                    bm25(fts_chunks) as score
                FROM fts_chunks f
                JOIN chunks c ON f.chunk_id = c.chunk_id
                WHERE fts_chunks MATCH ?
            """
            params = [escaped_query]
            
            if source:
                sql += " AND c.source = ?"
                params.append(source)
            
            sql += " ORDER BY score LIMIT ?"
            params.append(limit)
            
            try:
                cursor = conn.execute(sql, params)
                for row in cursor:
                    # Créer snippet (premiers 200 caractères)
                    text = row["text"] or ""
                    snippet = text[:200] + "..." if len(text) > 200 else text
                    
                    provenance = {}
                    if row["provenance_json"]:
                        provenance = json.loads(row["provenance_json"])
                    
                    results.append(SearchResult(
                        chunk_id=row["chunk_id"],
                        doc_id=row["doc_id"],
                        source=row["source"],
                        citation=row["citation"] or "",
                        pinpoint=row["pinpoint"] or "",
                        text_snippet=snippet,
                        score=abs(row["score"]),  # BM25 retourne des valeurs négatives
                        provenance=provenance,
                    ))
            except sqlite3.OperationalError as e:
                logger.warning(f"Search error: {e}")
        
        return results
    
    def lookup_by_origin_id(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup exact par origin_id.
        
        Args:
            origin_id: ID d'origine (LEGIARTI..., etc.)
            
        Returns:
            Dict avec doc + chunks, ou None si non trouvé
        """
        with self._get_conn() as conn:
            # Chercher le document
            cursor = conn.execute(
                "SELECT * FROM docs WHERE origin_id = ?",
                (origin_id,)
            )
            doc_row = cursor.fetchone()
            
            if not doc_row:
                return None
            
            doc_data = dict(doc_row)
            if doc_data.get("provenance_json"):
                doc_data["provenance"] = json.loads(doc_data["provenance_json"])
                del doc_data["provenance_json"]
            
            # Chercher les chunks associés
            cursor = conn.execute(
                "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
                (doc_data["doc_id"],)
            )
            
            chunks = []
            for row in cursor:
                chunk_data = dict(row)
                if chunk_data.get("provenance_json"):
                    chunk_data["provenance"] = json.loads(chunk_data["provenance_json"])
                    del chunk_data["provenance_json"]
                chunks.append(chunk_data)
            
            return {
                "doc": doc_data,
                "chunks": chunks,
            }
    
    def lookup_by_chunk_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup exact par chunk_id.
        
        Returns:
            Dict du chunk avec provenance, ou None
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM chunks WHERE chunk_id = ?",
                (chunk_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            data = dict(row)
            if data.get("provenance_json"):
                data["provenance"] = json.loads(data["provenance_json"])
                del data["provenance_json"]
            
            return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'index."""
        with self._get_conn() as conn:
            # Compter docs par source
            cursor = conn.execute("""
                SELECT source, COUNT(*) as count 
                FROM docs 
                GROUP BY source
            """)
            docs_by_source = {row["source"]: row["count"] for row in cursor}
            
            # Compter chunks par source
            cursor = conn.execute("""
                SELECT source, COUNT(*) as count 
                FROM chunks 
                GROUP BY source
            """)
            chunks_by_source = {row["source"]: row["count"] for row in cursor}
            
            # Totaux
            total_docs = sum(docs_by_source.values())
            total_chunks = sum(chunks_by_source.values())
        
        return {
            "total_docs": total_docs,
            "total_chunks": total_chunks,
            "docs_by_source": docs_by_source,
            "chunks_by_source": chunks_by_source,
            "db_path": str(self.db_path),
        }
    
    def chunk_exists(self, chunk_id: str) -> bool:
        """Vérifie si un chunk existe déjà."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM chunks WHERE chunk_id = ?",
                (chunk_id,)
            )
            return cursor.fetchone() is not None
    
    def doc_exists(self, doc_id: str) -> bool:
        """Vérifie si un document existe déjà."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM docs WHERE doc_id = ?",
                (doc_id,)
            )
            return cursor.fetchone() is not None
    
    def get_all_chunks_for_ids(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """Récupère plusieurs chunks par leurs IDs."""
        if not chunk_ids:
            return []
        
        with self._get_conn() as conn:
            placeholders = ",".join("?" * len(chunk_ids))
            cursor = conn.execute(
                f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})",
                chunk_ids
            )
            
            results = []
            for row in cursor:
                data = dict(row)
                if data.get("provenance_json"):
                    data["provenance"] = json.loads(data["provenance_json"])
                    del data["provenance_json"]
                results.append(data)
            
            return results
