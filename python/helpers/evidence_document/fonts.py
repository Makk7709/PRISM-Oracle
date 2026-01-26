"""
Evidence Document Fonts — TTF Registration for Full Unicode Support.

This module registers custom TrueType fonts with ReportLab to ensure:
- Full Unicode support (no black squares)
- Professional typography
- Consistent rendering across platforms

Fonts included:
- DejaVu Sans: Primary sans-serif (excellent Unicode coverage)
- DejaVu Serif: Serif alternative
- DejaVu Sans Mono: Monospace for code

Usage:
    from python.helpers.evidence_document.fonts import register_fonts, FONTS
    register_fonts()  # Call once at startup
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("evidence_document.fonts")

# Font directory (relative to project root)
FONTS_DIR = Path(__file__).parent.parent.parent.parent / "fonts"

# Font mappings: logical name -> (regular, bold, italic, bold-italic)
FONT_FAMILIES: Dict[str, Dict[str, str]] = {
    "DejaVu": {
        "regular": "DejaVuSans.ttf",
        "bold": "DejaVuSans-Bold.ttf",
        "italic": "DejaVuSans-Oblique.ttf",
        "bold-italic": "DejaVuSans-Bold.ttf",  # No bold-italic, use bold
    },
    "DejaVuSerif": {
        "regular": "DejaVuSerif.ttf",
        "bold": "DejaVuSerif-Bold.ttf",
        "italic": "DejaVuSerif.ttf",  # No italic, use regular
        "bold-italic": "DejaVuSerif-Bold.ttf",
    },
    "DejaVuMono": {
        "regular": "DejaVuSansMono.ttf",
        "bold": "DejaVuSansMono-Bold.ttf",
        "italic": "DejaVuSansMono.ttf",
        "bold-italic": "DejaVuSansMono-Bold.ttf",
    },
}

# Registered font names for use in templates
FONTS = {
    # Sans-serif (primary)
    "title": "DejaVu-Bold",
    "body": "DejaVu",
    "bold": "DejaVu-Bold",
    "italic": "DejaVu-Italic",
    
    # Serif
    "serif": "DejaVuSerif",
    "serif_bold": "DejaVuSerif-Bold",
    
    # Monospace
    "code": "DejaVuMono",
    "code_bold": "DejaVuMono-Bold",
    
    # Fallbacks to built-in (if TTF not available)
    "fallback_title": "Helvetica-Bold",
    "fallback_body": "Helvetica",
    "fallback_code": "Courier",
}

_fonts_registered = False


def register_fonts() -> bool:
    """
    Register custom TTF fonts with ReportLab.
    
    Returns:
        True if fonts registered successfully, False otherwise
    """
    global _fonts_registered
    
    if _fonts_registered:
        return True
    
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        if not FONTS_DIR.exists():
            logger.warning(f"Fonts directory not found: {FONTS_DIR}")
            return False
        
        registered = []
        
        # Register DejaVu Sans
        dejavu_regular = FONTS_DIR / "DejaVuSans.ttf"
        dejavu_bold = FONTS_DIR / "DejaVuSans-Bold.ttf"
        dejavu_italic = FONTS_DIR / "DejaVuSans-Oblique.ttf"
        
        if dejavu_regular.exists():
            pdfmetrics.registerFont(TTFont("DejaVu", str(dejavu_regular)))
            registered.append("DejaVu")
        
        if dejavu_bold.exists():
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(dejavu_bold)))
            registered.append("DejaVu-Bold")
        
        if dejavu_italic.exists():
            pdfmetrics.registerFont(TTFont("DejaVu-Italic", str(dejavu_italic)))
            registered.append("DejaVu-Italic")
        
        # Register font family for automatic bold/italic
        if all(f in registered for f in ["DejaVu", "DejaVu-Bold", "DejaVu-Italic"]):
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                "DejaVu",
                normal="DejaVu",
                bold="DejaVu-Bold",
                italic="DejaVu-Italic",
                boldItalic="DejaVu-Bold"  # No bold-italic available
            )
        
        # Register DejaVu Serif
        serif_regular = FONTS_DIR / "DejaVuSerif.ttf"
        serif_bold = FONTS_DIR / "DejaVuSerif-Bold.ttf"
        
        if serif_regular.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSerif", str(serif_regular)))
            registered.append("DejaVuSerif")
        
        if serif_bold.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSerif-Bold", str(serif_bold)))
            registered.append("DejaVuSerif-Bold")
        
        if "DejaVuSerif" in registered and "DejaVuSerif-Bold" in registered:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                "DejaVuSerif",
                normal="DejaVuSerif",
                bold="DejaVuSerif-Bold",
                italic="DejaVuSerif",
                boldItalic="DejaVuSerif-Bold"
            )
        
        # Register DejaVu Mono (for code)
        mono_regular = FONTS_DIR / "DejaVuSansMono.ttf"
        mono_bold = FONTS_DIR / "DejaVuSansMono-Bold.ttf"
        
        if mono_regular.exists():
            pdfmetrics.registerFont(TTFont("DejaVuMono", str(mono_regular)))
            registered.append("DejaVuMono")
        
        if mono_bold.exists():
            pdfmetrics.registerFont(TTFont("DejaVuMono-Bold", str(mono_bold)))
            registered.append("DejaVuMono-Bold")
        
        if "DejaVuMono" in registered and "DejaVuMono-Bold" in registered:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                "DejaVuMono",
                normal="DejaVuMono",
                bold="DejaVuMono-Bold",
                italic="DejaVuMono",
                boldItalic="DejaVuMono-Bold"
            )
        
        _fonts_registered = True
        logger.info(f"Registered fonts: {', '.join(registered)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to register fonts: {e}")
        return False


def get_font(role: str, fallback: bool = True) -> str:
    """
    Get font name for a given role.
    
    Args:
        role: Font role (title, body, code, etc.)
        fallback: If True, return built-in font if custom not available
        
    Returns:
        Font name to use
    """
    # Ensure fonts are registered
    register_fonts()
    
    font = FONTS.get(role)
    if font and is_font_available(font):
        return font
    
    if fallback:
        fallback_key = f"fallback_{role}"
        return FONTS.get(fallback_key, "Helvetica")
    
    return font or "Helvetica"


def is_font_available(font_name: str) -> bool:
    """Check if a font is registered and available."""
    try:
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.getFont(font_name)
        return True
    except:
        return False


# Auto-register fonts on import
register_fonts()
