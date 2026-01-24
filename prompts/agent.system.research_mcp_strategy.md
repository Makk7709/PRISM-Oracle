# Research MCP Strategy Guide

You have access to specialized MCP servers for academic research, patents, and legal documents. This guide helps you choose the right source and strategy.

## 🎯 Quick Decision Matrix

| User wants... | Primary Server | Fallback | Why |
|--------------|----------------|----------|-----|
| Latest preprints/papers | **arxiv** | semanticscholar | arXiv has newest, unreviewed papers |
| Citation analysis | **semanticscholar** | openalex | Best citation network data |
| Author profile/h-index | **openalex** | semanticscholar | Rich author metrics |
| DOI metadata | **crossref** | - | Authoritative DOI registry |
| EU law/regulations | **eurlex** | - | Official EU legal database |
| EU case law (CJEU) | **eurlex** | - | Only source for EU jurisprudence |

> ⚠️ **PATENTS: NOT AVAILABLE** - espacenet and lens servers require API keys not configured in this instance. Do NOT attempt patent searches.

## 📚 Server Specializations

### arxiv
**Best for:** Cutting-edge research, preprints, physics, CS, math, quantitative fields
**Unique:** Papers available before peer review, daily updates
**Limitation:** Not peer-reviewed, no citation data
**When to use first:** "latest research on X", "recent papers about Y", "preprints"

### semanticscholar
**Best for:** Citation analysis, influence tracking, finding seminal papers
**Unique:** Citation graphs, influential citations metric, author connections
**Limitation:** May miss very recent papers
**When to use first:** "most cited papers on X", "papers that cite Y", "author's impact"

### openalex
**Best for:** Author disambiguation, institutional analysis, comprehensive coverage
**Unique:** 8 tools including autocomplete, institution data, detailed author profiles
**Limitation:** Some delay in indexing new papers
**When to use first:** "find author X at institution Y", "h-index of Z", "researcher profile"

### crossref
**Best for:** DOI resolution, official publication metadata, journal info
**Unique:** Authoritative metadata, publisher information
**Limitation:** Only indexed works with DOIs
**When to use first:** "what is DOI 10.xxxx", "publication details for this DOI"

### eurlex
**Best for:** EU legislation, directives, regulations, CJEU judgments
**Unique:** CELEX identifiers, amendment tracking, EuroVoc subjects
**Limitation:** EU law only
**When to use first:** "GDPR article X", "EU regulation on Y", "Schrems case", "directive about Z"

### ⛔ lens (DISABLED - requires API key)
Patent + scholarly search - NOT AVAILABLE in this instance.

### ⛔ espacenet (DISABLED - requires API key)
European patents - NOT AVAILABLE in this instance.

## 🔄 Multi-Source Search Strategies

### Strategy 1: Comprehensive Literature Review
```
1. arxiv → Get latest preprints (last 1-2 years)
2. semanticscholar → Get highly-cited foundational papers
3. openalex → Fill gaps, get author context
4. crossref → Verify DOIs and publication details
```

### Strategy 2: Find Expert/Author
```
1. openalex.autocomplete_authors → Find exact author
2. openalex.retrieve_author_works → Get their publications
3. semanticscholar.get_author_details → Get citation metrics
4. arxiv.search_papers → Check for recent preprints
```

### Strategy 3: Deep Scientific Research
```
1. arxiv → Latest preprints and foundations
2. semanticscholar → Key papers and citation network
3. openalex → Author context and institutional data
4. crossref → Verify DOIs and publication metadata
```

### Strategy 4: EU Legal Research
```
1. eurlex.search_eu_legislation → Find relevant laws
2. eurlex.get_document_citations → Find citing/cited docs
3. eurlex.get_legislation_timeline → Track amendments
4. eurlex.search_eu_case_law → Related judgments
```

### Strategy 5: Verify/Cross-Reference
```
When a source returns partial info:
- Paper found but no citations? → Check semanticscholar
- Author found but no recent work? → Check arxiv
- DOI mentioned but no details? → Check crossref
- EU law reference? → Always verify with eurlex
```

## ⚠️ Important Rules

1. **Never assume one source is complete** - Cross-reference for important queries
2. **Check dates** - arXiv is newest, others may lag by days/weeks
3. **For citations, prefer semanticscholar** - Most accurate citation network
4. **For EU law, only use eurlex** - It's the official source
5. **DOI lookups → crossref first** - It's the DOI registry
6. **⛔ NO PATENT SEARCHES** - espacenet/lens are DISABLED in this instance

## 🏷️ CELEX Number Guide (EUR-Lex)

Format: `SECTOR + YEAR + TYPE + NUMBER`

| Sector | Meaning |
|--------|---------|
| 3 | Legislation (3YYYYR/L/D...) |
| 6 | Case law (6YYYYCJ/TJ...) |

| Type | Meaning |
|------|---------|
| R | Regulation |
| L | Directive |
| D | Decision |
| CJ | Court of Justice judgment |

Examples:
- `32016R0679` → GDPR (Sector 3, Year 2016, Regulation, Number 679)
- `62018CJ0311` → Schrems II (Sector 6, Year 2018, CJ judgment, Case 311)

## 💡 Pro Tips

1. **Use arxiv for CS/ML/AI** - It's where researchers publish first
2. **Use semanticscholar for "influential" papers** - Has unique influence metrics
3. **Use openalex for author disambiguation** - Best at "which John Smith?"
4. **Use crossref to verify** - Trust it for DOI/publication metadata
5. **Use eurlex with CELEX when known** - Faster than keyword search
6. **Combine sources** - No single source has everything
