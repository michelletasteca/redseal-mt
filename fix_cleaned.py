"""
Create *-cleaned-v1.txt by fixing OCR artifacts in *-cleaned.txt files.
No API key needed — all fixes are deterministic text substitutions.
"""
from pathlib import Path

# (exact_string_to_find, replacement)
FIXES = [
    # fi/fl/ff ligature splits
    ("transf erring",   "transferring"),
    ("transf er ",      "transfer "),        # "transfer sheets", "transfer to"
    ("equip ment",      "equipment"),
    ("def ective",      "defective"),
    ("Def ibrillator",  "Defibrillator"),
    ("biolo gical",     "biological"),
    ("verif y",         "verify"),
    ("verif ied",       "verified"),
    ("f ixed",          "fixed"),
    ("f ace-to-f ace",  "face-to-face"),
    ("ref lecting",     "reflecting"),
    ("dif f erences",   "differences"),
    ("dif ferences",    "differences"),       # inconsistent OCR on same word
    ("inf usion",       "infusion"),
    ("f ermentation",   "fermentation"),
    ("b roiling",       "broiling"),
    ("veg etables",     "vegetables"),
    ("s oaking",        "soaking"),
    ("f ats",           "fats"),
    ("muf f ins",       "muffins"),
    ("prof iteroles ,",  "profiteroles,"),    # space + comma
    ("prof iteroles,",  "profiteroles,"),
    ("prof iteroles\n", "profiteroles\n"),   # end of line
    ("prof iteroles ",  "profiteroles "),
    ("profiteroles ,",  "profiteroles,"),    # trailing space from prior fix
    ("two -stage",      "two-stage"),
    ("mustard -based",  "mustard-based"),
    ("s hutting",       "shutting"),
    # Extra space before punctuation
    ("dry goods ,",     "dry goods,"),
]


def fix_text(text: str) -> str:
    for bad, good in FIXES:
        text = text.replace(bad, good)
    return text


def main():
    pdf_dir = Path("pdf")
    cleaned_files = sorted(pdf_dir.glob("*-cleaned.txt"))

    if not cleaned_files:
        print("No *-cleaned.txt files found in pdf/")
        return

    for src in cleaned_files:
        letter = src.stem.split("-")[0]
        dst = pdf_dir / f"{letter}-cleaned-v1.txt"

        original = src.read_text(encoding="utf-8")
        fixed = fix_text(original)

        changes = sum(1 for (b, g) in FIXES if b in original)
        dst.write_text(fixed, encoding="utf-8")
        print(f"{letter}: {changes} fix type(s) applied -> {dst.name}")


if __name__ == "__main__":
    main()
