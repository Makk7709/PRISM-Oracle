"""Outil ponctuel : auto-héberge les polices Google (Playfair Display + Space Grotesk).

Télécharge les woff2 des sous-ensembles latin/latin-ext pour les graisses utilisées
par index.html (Playfair 400-700, Space Grotesk 400-700) et login.html (Space Grotesk
300-600), puis génère webui/public/fonts/korev-fonts.css avec des URL locales.

Supprime la dépendance à fonts.googleapis.com / fonts.gstatic.com (SonarQube Web:S5725
+ bénéfice RGPD : plus d'appel tiers au chargement).
"""

import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(ROOT, "webui", "public", "fonts")
CSS_OUT = os.path.join(FONTS_DIR, "korev-fonts.css")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
CSS_URLS = [
    # Typographie KOREV (index.html / login.html / welcome-screen.html)
    "https://fonts.googleapis.com/css2?"
    "family=Playfair+Display:wght@400;500;600;700&"
    "family=Space+Grotesk:wght@300;400;500;600;700&display=swap",
    # Polices héritées encore référencées en CSS : Rubik (buttons.css) +
    # Roboto Mono (fallback code dans index.css). Graisses statiques explicites.
    "https://fonts.googleapis.com/css2?"
    "family=Rubik:wght@400;500;700&"
    "family=Roboto+Mono:wght@400;500&display=swap",
]
KEEP_SUBSETS = {"latin", "latin-ext"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    os.makedirs(FONTS_DIR, exist_ok=True)
    out_faces = []
    downloaded = {}

    for css_url in CSS_URLS:
        css = fetch(css_url).decode("utf-8")
        # Découpe en blocs précédés de leur commentaire de sous-ensemble : /* latin */
        blocks = re.split(r"/\*\s*([\w-]+)\s*\*/", css)
        # blocks = ['', subset1, css1, subset2, css2, ...]
        for i in range(1, len(blocks) - 1, 2):
            subset = blocks[i].strip()
            body = blocks[i + 1]
            if subset not in KEEP_SUBSETS:
                continue
            fam = re.search(r"font-family:\s*'([^']+)'", body)
            wght = re.search(r"font-weight:\s*(\d+)", body)
            url = re.search(r"url\((https://[^)]+\.woff2)\)", body)
            urange = re.search(r"unicode-range:\s*([^;]+);", body)
            if not (fam and wght and url):
                continue
            slug = fam.group(1).replace(" ", "")
            fname = f"{slug}-{wght.group(1)}-{subset}.woff2"
            if fname not in downloaded:
                data = fetch(url.group(1))
                with open(os.path.join(FONTS_DIR, fname), "wb") as f:
                    f.write(data)
                downloaded[fname] = len(data)
            ur = f"\n  unicode-range: {urange.group(1).strip()};" if urange else ""
            out_faces.append(
                "@font-face {\n"
                f"  font-family: '{fam.group(1)}';\n"
                "  font-style: normal;\n"
                f"  font-weight: {wght.group(1)};\n"
                "  font-display: swap;\n"
                f"  src: url('{fname}') format('woff2');{ur}\n"
                "}"
            )

    header = (
        "/* Polices auto-hébergées (Playfair Display, Space Grotesk).\n"
        "   Généré par scripts/_vendor_fonts.py — supprime la dépendance Google Fonts\n"
        "   (SonarQube Web:S5725 + RGPD : aucun appel tiers au chargement). */\n\n"
    )
    with open(CSS_OUT, "w", encoding="utf-8") as f:
        f.write(header + "\n\n".join(out_faces) + "\n")

    print(f"{len(downloaded)} woff2 téléchargés dans {FONTS_DIR}")
    print(f"CSS généré : {CSS_OUT} ({len(out_faces)} @font-face)")


if __name__ == "__main__":
    main()
