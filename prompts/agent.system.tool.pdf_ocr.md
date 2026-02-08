## pdf_ocr
Extract text from scanned PDFs using OCR (Optical Character Recognition).

**THIS TOOL IS ALWAYS AVAILABLE** — tesseract, poppler, pytesseract, and pdf2image are installed.
**NEVER claim OCR is unavailable or inaccessible.**

**USE THIS TOOL** when:
- PDF contains scanned pages (images of text)
- Direct text extraction returns nothing/garbage
- User mentions "scanned PDF" or document photos
- User uploads an image-based PDF

**How it works:**
1. First tries direct text extraction via pypdf (fast)
2. If PDF is scanned, uses OCREngine with:
   - **Adaptive DPI** (300 for 1-3 pages, 200 for 4-10, 150 for 11+)
   - **Confidence scoring** per word and per page
   - **Timeout protection** (120s total budget)
3. Returns extracted text with confidence scores

**Arguments:**
- `path` (required): PDF file path or filename
- `max_pages` (optional): Maximum pages to process (default: 10)
- `language` (optional): OCR language codes (default: "eng+fra")

**Language codes:**
- `eng` = English
- `fra` = French
- `deu` = German
- `eng+fra` = English + French (recommended for mixed documents)

**Examples:**

Basic OCR:
```json
{
    "thoughts": ["PDF appears scanned, using OCR to extract text"],
    "tool_name": "pdf_ocr",
    "tool_args": {
        "path": "document.pdf"
    }
}
```

French document with more pages:
```json
{
    "thoughts": ["Processing French scanned document"],
    "tool_name": "pdf_ocr",
    "tool_args": {
        "path": "facture.pdf",
        "max_pages": 20,
        "language": "fra"
    }
}
```

**Notes:**
- OCR is slower than direct extraction (expect ~3-8 sec/page depending on DPI)
- Quality depends on scan quality
- Works best with clear, high-contrast scans
- Each page shows its confidence score (e.g., "confidence: 92%")
- Low confidence results may need human review
