## Environment
- Working directory: {{work_dir}}
- File uploads: {{work_dir}}/tmp/uploads/
- Python execution: Available via code_execution tool (runtime: python)

### File Access Rules
- User-uploaded files are ALWAYS in: {{work_dir}}/tmp/uploads/
- ALWAYS use the full absolute path when accessing files
- For Excel files (.xlsx): use pandas.read_excel() via code_execution
- For CSV files: use pandas.read_csv() via code_execution
- For PDF files: use pypdf or pdfplumber via code_execution
- NEVER assume files are inaccessible - they are local and readable
- ALWAYS verify file paths before claiming they don't exist