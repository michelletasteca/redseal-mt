"""
Re-extract Red Seal Cook PDFs using Claude's native PDF reading.
Produces {letter}-cleaned-v1.txt files that fix OCR artifacts and remove
page headers/footers, using the PDF itself as the authoritative source.
"""
import anthropic
import base64
from pathlib import Path

client = anthropic.Anthropic()

EXTRACT_PROMPT = """\
Extract the complete text from this Red Seal Cook Occupational Standard PDF.

Rules:
1. Remove page headers and footers — that means the page number (e.g. "34") and the line \
"Red Seal Occupational Standard - Cook" that appear at the bottom of every page.
2. Fix all OCR split-word artifacts — words that were incorrectly split with a space, e.g.:
   - "transf erring" → "transferring"
   - "equip ment" → "equipment"
   - "def ective" → "defective"
   - "Def ibrillator" → "Defibrillator"
   - "verif y" → "verify"
   - "biolo gical" → "biological"
   - "s hutting" → "shutting"
   Fix any similar split-word artifacts you encounter.
3. Preserve all structural content exactly as it appears in the document:
   - MAJOR WORK ACTIVITY heading and subtitle
   - TASK headings and TASK DESCRIPTOR paragraphs
   - Sub-task headings (e.g. A-1.01, A-1.02) with their full title
   - Jurisdiction tables (NL NS PE NB QC ON MB SK AB BC NT YT NU / yes/NV rows)
   - SKILLS section with Performance Criteria and Evidence of Attainment columns
   - RANGE OF VARIABLES sections with all their bullet items
   - KNOWLEDGE section with Learning Outcomes and Learning Objectives columns
   - All sub-task codes (A-1.01.01P, A-1.01.01L, etc.)
4. Output plain text only — no markdown, no asterisks, no bold markers.
5. Use a single blank line between sub-task blocks and sections. Do not add extra blank lines.
"""


def extract_pdf(pdf_path: Path) -> str:
    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=[{
            "type": "text",
            "text": "You are a precise document transcription assistant. Extract text exactly as instructed.",
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    }
                },
                {
                    "type": "text",
                    "text": EXTRACT_PROMPT
                }
            ]
        }],
    ) as stream:
        message = stream.get_final_message()
        usage = message.usage
        print(f"     Tokens — input: {usage.input_tokens}, output: {usage.output_tokens}")
        return message.content[0].text


def main():
    pdf_dir = Path("pdf")

    pdf_files = sorted(pdf_dir.glob("*-Red Seal.pdf"))
    if not pdf_files:
        print("No *-Red Seal.pdf files found in pdf/")
        return

    for pdf_path in pdf_files:
        letter = pdf_path.name.split("-")[0]
        output_path = pdf_dir / f"{letter}-cleaned-v1.txt"

        if output_path.exists():
            print(f"Skipping {letter} (already exists: {output_path})")
            continue

        print(f"Processing {letter} ({pdf_path.name})...")
        clean_text = extract_pdf(pdf_path)
        output_path.write_text(clean_text, encoding="utf-8")
        print(f"  -> Written to {output_path}")


if __name__ == "__main__":
    main()
