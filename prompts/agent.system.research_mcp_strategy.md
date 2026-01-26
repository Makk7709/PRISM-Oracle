# Research MCP Strategy Guide

You have access to specialized MCP servers for academic research. This guide helps you choose the right source and strategy.

## 🎯 Quick Decision Matrix

| User wants... | Primary Server | Fallback | Why |
|--------------|----------------|----------|-----|
| Latest preprints/papers | **arxiv** | semanticscholar | arXiv has newest, unreviewed papers |
| Citation analysis | **semanticscholar** | openalex | Best citation network data |
| Author profile/h-index | **openalex** | semanticscholar | Rich author metrics |
| Web search/general info | **tavily** | firecrawl | AI-powered web search |
| Web scraping | **firecrawl** | - | Extract content from URLs |
| EU law/regulations | **tavily** (search) | code_execution (scrape) | Search legal databases via web |

> ⚠️ **NOT AVAILABLE in this instance:**
> - **eurlex** - EUR-Lex MCP not configured (use tavily to search EUR-Lex website)
> - **crossref** - CrossRef MCP not configured
> - **espacenet/lens** - Patent servers require API keys not configured

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

### tavily
**Best for:** General web search, current information, legal research via web
**Unique:** AI-powered search with relevance ranking
**Limitation:** Requires TAVILY_API_KEY in .env
**When to use first:** "search for X", "find information about Y", "EU law on Z"

### firecrawl
**Best for:** Web scraping, extracting content from specific URLs
**Unique:** Clean text extraction from web pages
**Limitation:** Requires FIRECRAWL_API_KEY in .env
**When to use first:** "extract content from URL", "scrape this page"

### ⛔ crossref (NOT CONFIGURED)
DOI metadata - NOT AVAILABLE in this instance. Use tavily to search.

### ⛔ eurlex (NOT CONFIGURED)
EU legislation database - NOT AVAILABLE in this instance. 
**WORKAROUND:** Use `tavily.search` with query like "site:eur-lex.europa.eu GDPR article 6"

### ⛔ lens (NOT CONFIGURED)
Patent + scholarly search - NOT AVAILABLE in this instance.

### ⛔ espacenet (NOT CONFIGURED)
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

### Strategy 4: EU Legal Research (without eurlex MCP)
```
1. tavily.search "site:eur-lex.europa.eu [topic]" → Find EU legislation
2. tavily.search "[directive/regulation name] consolidated version" → Get current text
3. firecrawl.scrape_url [eur-lex URL] → Extract full document if needed
4. code_execution (Python) → Parse and analyze legal text
```
> Note: eurlex MCP is not configured. Use web search as workaround.

### Strategy 5: Verify/Cross-Reference
```
When a source returns partial info:
- Paper found but no citations? → Check semanticscholar
- Author found but no recent work? → Check arxiv
- DOI mentioned but no details? → Use tavily to search DOI
- EU law reference? → Use tavily with "site:eur-lex.europa.eu"
```

## ⚠️ Important Rules

1. **Never assume one source is complete** - Cross-reference for important queries
2. **Check dates** - arXiv is newest, others may lag by days/weeks
3. **For citations, prefer semanticscholar** - Most accurate citation network
4. **For EU law** - Use `tavily.search` with "site:eur-lex.europa.eu" (eurlex MCP not configured)
5. **For general web info** - Use `tavily.search` first
6. **⛔ NO PATENT SEARCHES** - espacenet/lens are NOT CONFIGURED in this instance

## 🏷️ CELEX Number Guide (EUR-Lex)

> Note: Use CELEX numbers when searching via tavily for better precision.

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

**Search example:** `tavily.search "32016R0679 site:eur-lex.europa.eu"`

## 💡 Pro Tips

1. **Use arxiv for CS/ML/AI** - It's where researchers publish first
2. **Use semanticscholar for "influential" papers** - Has unique influence metrics
3. **Use openalex for author disambiguation** - Best at "which John Smith?"
4. **Use tavily for general search** - AI-powered web search
5. **For EU law, use tavily + site:eur-lex.europa.eu** - Workaround since eurlex MCP not configured
6. **Combine sources** - No single source has everything
