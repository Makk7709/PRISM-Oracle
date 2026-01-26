## file_writer
Create files (PDF, CSV, Excel, text) without writing code.

**USE THIS TOOL** when you need to:
- Generate a PDF report or document
- Create a CSV file with data
- Create an Excel spreadsheet
- Write any text file

**Arguments:**
- `filename` (required): Output filename (without path)
- `content` (required): The content to write
- `format` (optional): "pdf", "csv", "excel", "txt", "json", "md" (auto-detected from extension)
- `title` (optional): Title for PDF documents

**Output:** Files are saved to `tmp/generated/` with timestamp.

**Examples:**

Create a PDF report:
```json
{
    "thoughts": ["Creating classification report as PDF"],
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "rapport_classement.pdf",
        "title": "Rapport de Classification des Documents",
        "content": "# Documents par Client\n\n## Client A\n- Document 1\n- Document 2\n\n## Client B\n- Document 3"
    }
}
```

Create a CSV file:
```json
{
    "thoughts": ["Exporting data to CSV"],
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "export.csv",
        "content": "Client,Code,Documents\nACME,101,5\nTechCorp,102,3"
    }
}
```

Create an Excel file:
```json
{
    "thoughts": ["Creating Excel spreadsheet"],
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "data.xlsx",
        "content": "Name,Value,Status\nItem1,100,Active\nItem2,200,Pending"
    }
}
```

**Content format for CSV/Excel:**
- First line = headers
- Following lines = data rows
- Use commas or semicolons as separators

**Content format for PDF (Full Markdown support):**

Le générateur PDF supporte **tout le Markdown** :

- **Headers**: `# H1`, `## H2`, `### H3`, `#### H4`
- **Bold/Italic**: `**bold**`, `*italic*`
- **Listes à puces**: `- item` ou `* item`
- **Listes numérotées**: `1. item`
- **Tableaux**: format Markdown standard
- **Code blocks**: ` ```code``` `
- **Blockquotes**: `> quote`
- **Liens**: `[text](url)`
- **Lignes horizontales**: `---`

**Exemple de PDF bien formaté:**
```json
{
    "tool_name": "file_writer",
    "tool_args": {
        "filename": "analyse_strategique.pdf",
        "title": "Analyse Stratégique - Client XYZ",
        "content": "## Executive Summary\n\n> **Recommandation** : Procéder à l'acquisition pour €50M\n\n## Analyse MECE\n\n### Branche 1 : Synergies\n\n- Synergie coûts : **€5M/an**\n- Synergie revenus : **€3M/an**\n\n### Branche 2 : Risques\n\n| Risque | Probabilité | Impact |\n|--------|-------------|--------|\n| Intégration | Moyen | Élevé |\n| Marché | Faible | Moyen |\n\n## Prochaines Étapes\n\n1. Due diligence approfondie\n2. Négociation finale\n3. Closing prévu Q2\n\n---\n\n*Document généré par Korev Evidence*"
    }
}
```

**Le PDF généré inclura :**
- En-têtes et pieds de page professionnels
- Numérotation des pages
- Couleurs et styles cohérents
- Tableaux avec alternance de couleurs
- Mise en page soignée
