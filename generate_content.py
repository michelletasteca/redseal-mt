import anthropic
from pathlib import Path

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert educational content creator specializing in Red Seal Cook certification exam preparation. Given the official Red Seal Occupational Standard content for cooks, generate a comprehensive learning module in Markdown with exactly three sections:

## Study Guide
A clear, organized summary covering all tasks, sub-tasks, skills, and key knowledge points. Use headings, bullet points, and concise explanations so learners can quickly review the material.

## Flashcards
A markdown table with columns | Term | Definition | covering all key terminology, regulations, equipment, techniques, and concepts from the content.

## Quiz Questions
10 numbered multiple-choice questions (options A, B, C, D) drawn from the learning objectives and knowledge points. After all 10 questions, include an **Answer Key** section listing the correct letter for each question."""


def generate_module(content: str) -> str:
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{
            "role": "user",
            "content": f"Create a full learning module for the following Red Seal Cook standard content:\n\n{content}"
        }]
    ) as stream:
        message = stream.get_final_message()
        usage = message.usage
        print(f"     Tokens — input: {usage.input_tokens}, output: {usage.output_tokens}, "
              f"cache_read: {getattr(usage, 'cache_read_input_tokens', 0)}, "
              f"cache_write: {getattr(usage, 'cache_creation_input_tokens', 0)}")
        return message.content[0].text


def main():
    pdf_dir = Path("pdf")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    cleaned_files = sorted(pdf_dir.glob("*-cleaned.txt"))
    if not cleaned_files:
        print("No *-cleaned.txt files found in pdf/")
        return

    for file_path in cleaned_files:
        letter = file_path.stem.split("-")[0]
        output_path = output_dir / f"{letter}-module.md"

        if output_path.exists():
            print(f"Skipping {letter} (already exists: {output_path})")
            continue

        print(f"Processing Major Work Activity {letter}...")
        content = file_path.read_text(encoding="utf-8")
        module = generate_module(content)
        output_path.write_text(module, encoding="utf-8")
        print(f"  -> Written to {output_path}")


if __name__ == "__main__":
    main()
