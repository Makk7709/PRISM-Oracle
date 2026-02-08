## code_execution — YOUR UNIVERSAL TOOL

**CRITICAL:** `code_execution` is your most powerful tool. You can solve ANY programming task with it.

### When to Use
- Reading ANY file format (Excel, CSV, PDF, images, etc.)
- Creating ANY file format (PDF, Excel, CSV, reports, etc.)
- Data processing, analysis, transformation
- Web scraping, API calls
- File management (copy, move, rename, organize)
- ANY task that can be done with Python code

### NEVER Say "MISSING_TOOL"
If you think a specific tool is missing, **use code_execution instead**.

Examples of what you CAN do with code_execution:

**Read Excel:**
```json
{
    "tool_name": "code_execution",
    "tool_args": {
        "runtime": "python",
        "code": "import pandas as pd\ndf = pd.read_excel('/path/to/file.xlsx')\nprint(df.to_string())"
    }
}
```

**Create PDF:**
```json
{
    "tool_name": "code_execution",
    "tool_args": {
        "runtime": "python",
        "code": "from reportlab.lib.pagesizes import A4\nfrom reportlab.pdfgen import canvas\nc = canvas.Canvas('/path/output.pdf', pagesize=A4)\nc.drawString(100, 750, 'Title')\nc.save()\nprint('PDF created')"
    }
}
```

**Analyze PDF:**
```json
{
    "tool_name": "code_execution",
    "tool_args": {
        "runtime": "python",
        "code": "import fitz\ndoc = fitz.open('/path/to/file.pdf')\nfor page in doc:\n    print(page.get_text())"
    }
}
```

**Organize files:**
```json
{
    "tool_name": "code_execution",
    "tool_args": {
        "runtime": "python",
        "code": "import os, shutil\nfor f in os.listdir('/path'):\n    if f.endswith('.pdf'):\n        shutil.move(f'/path/{f}', f'/dest/{f}')"
    }
}
```

### Available Python Libraries
- `pandas` — Excel, CSV, data analysis
- `openpyxl` — Excel files
- `pypdf` — PDF reading
- `pdfplumber` — PDF reading with table extraction
- `reportlab` — PDF creation
- `Pillow` — Image processing
- `requests` — HTTP/API calls
- `os`, `shutil` — File operations
- Standard library (json, csv, re, etc.)

### Key Paths
- User uploads: `{{work_dir}}/tmp/uploads/`
- Generated files: `{{work_dir}}/tmp/generated/`

### Rule
**NEVER respond with MISSING_TOOL for tasks that can be done with Python.**
Use code_execution and write the code yourself.
