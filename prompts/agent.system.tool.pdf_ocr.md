## pdf_ocr
Extract text from scanned PDFs using OCR (Optical Character Recognition).

**USE THIS TOOL** when:
- PDF contains scanned pages (images of text)
- Direct text extraction returns nothing/garbage
- User mentions "scanned PDF" or document photos

**How it works:**
1. First tries direct text extraction (fast)
2. If PDF is scanned, converts to images and runs Tesseract OCR
3. Returns all extracted text

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
- OCR is slower than direct extraction (expect ~5-10 sec/page)
- Quality depends on scan quality
- Works best with clear, high-contrast scans
