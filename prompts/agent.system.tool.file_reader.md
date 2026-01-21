## file_reader
Read files directly without writing code. Supports Excel, CSV, PDF, and text files.

**USE THIS TOOL** when you need to:
- Read an Excel file (.xlsx, .xls)
- Read a CSV file
- Read a PDF document
- Read any text file

**Arguments:**
- `path` (required): File path or filename. Can be:
  - Just filename: `"Listing_client_code.xlsx"` (searches in uploads)
  - Relative path: `"tmp/uploads/file.xlsx"`
  - Absolute path: `"/full/path/to/file.xlsx"`
- `max_rows` (optional): Maximum rows to read for Excel/CSV (default: 100)

**Examples:**

Read an Excel file:
```json
{
    "thoughts": ["Reading client listing Excel file"],
    "tool_name": "file_reader",
    "tool_args": {
        "path": "Listing_client_code.xlsx"
    }
}
```

Read a CSV with more rows:
```json
{
    "thoughts": ["Reading large CSV file"],
    "tool_name": "file_reader",
    "tool_args": {
        "path": "data.csv",
        "max_rows": 500
    }
}
```

Read a PDF:
```json
{
    "thoughts": ["Extracting text from PDF document"],
    "tool_name": "file_reader",
    "tool_args": {
        "path": "document.pdf"
    }
}
```

**Important:**
- Files uploaded by user are in `tmp/uploads/` folder
- If file not found, the tool will show available files
- For Excel/CSV: shows column names and data
- For PDF: extracts text content (may be empty for scanned PDFs)
