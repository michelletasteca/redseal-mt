"""
Convert *-cleaned-v1.txt → *-cleaned-v2.txt with a clean bullet-based format.
No table layout, no jurisdiction rows.
"""
import re
from pathlib import Path

# ── Regex patterns ─────────────────────────────────────────────────────────────
MAJOR_RE    = re.compile(r'^MAJOR WORK ACTIVITY ([A-Z])\s*$')
TASK_RE     = re.compile(r'^TASK ([A-Z]-\d+) (.+)$')
TASKDESC_RE = re.compile(r'^TASK DESCRIPTOR\s*$')
SUBTASK_RE  = re.compile(r'^ {0,5}([A-Z]-\d+\.\d{2}) {1,}(.+?)\s*$')
PROVINCE_RE = re.compile(r'NL\s+NS\s+PE\s+NB')           # jurisdiction header
YESNV_RE    = re.compile(r'^\s*(yes|NV)(\s+(yes|NV))+\s*$')  # yes/NV row
SKILLS_RE   = re.compile(r'^\s*SKILLS\s*$')
KNOWLEDGE_RE= re.compile(r'^\s*KNOWLEDGE\s*$')
RANGE_RE    = re.compile(r'^RANGE OF VARIABLES\s*$')
PC_HDR_RE   = re.compile(r'Performance Criteria\s+Evidence of Attainment')
LO_HDR_RE   = re.compile(r'Learning Outcomes\s+Learning Objectives')
CODE_P_RE   = re.compile(r'^ {0,6}([A-Z]-\d+\.\d+\.\d+P) {2,}(.*)')
CODE_L_RE   = re.compile(r'^ {0,6}([A-Z]-\d+\.\d+\.\d+L) {2,}(.*)')

# Verbs that typically start a Learning Objective sentence
OBJ_VERBS = frozenset({
    'define', 'identify', 'describe', 'interpret', 'demonstrate', 'explain',
    'apply', 'analyze', 'analyse', 'list', 'recognize', 'recognise', 'compare',
    'use', 'select', 'perform', 'state', 'outline', 'evaluate', 'assess',
    'distinguish', 'calculate', 'develop', 'create', 'plan', 'organize',
    'implement', 'conduct', 'manage', 'prepare', 'follow',
    'maintain', 'prevent', 'reduce', 'control', 'monitor', 'record',
    'communicate', 'coordinate', 'handle', 'operate', 'classify', 'discuss',
    'determine', 'summarize', 'summarise', 'verify', 'examine', 'inspect',
    'read', 'choose', 'review', 'check',
})

# Words that indicate a line wraps mid-thought (not a sentence end)
CONT_ENDS = frozenset({
    'and', 'or', 'the', 'a', 'an', 'to', 'for', 'of', 'in', 'at', 'on',
    'with', 'by', 'from', 'that', 'which', 'their', 'its', 'as', 'into',
    'through', 'both', 'not', 'without', 'against', 'before', 'after',
    'between', 'including', 'associated', 'pertaining', 'relating', 'required',
    'used', 'are', 'is', 'be', 'been', 'using', 'such', 'per',
})


# ── Column splitting helpers ────────────────────────────────────────────────────

def find_right_col_start(first_line, code_end):
    """Return absolute char position where right column starts in first_line."""
    rest = first_line[code_end:]
    gap = re.search(r' {3,}', rest)
    if gap:
        return code_end + gap.end()
    return None


def split_at_gap(text):
    """Split 'text' at first run of 3+ spaces → (left, right)."""
    gap = re.search(r' {3,}', text)
    if gap:
        return text[:gap.start()].strip(), text[gap.end():].strip()
    return text.strip(), ''


def parse_two_col_block(lines, code_re):
    """
    Given lines that form a single code entry, return
    (code, left_text, right_text).
    Right_text is a joined string; caller splits into objectives if needed.
    """
    first = lines[0]
    m = code_re.match(first)
    code = m.group(1)
    code_end = m.start(2)       # absolute position after code + whitespace

    # First line: determine right-col absolute start
    rest_of_first = first[code_end:]
    left_start, right_start = split_at_gap(rest_of_first)
    right_abs = find_right_col_start(first, code_end)

    left_parts  = [left_start]  if left_start  else []
    right_parts = [right_start] if right_start else []

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        leading = len(line) - len(line.lstrip(' '))

        if right_abs and leading >= right_abs - 4:
            # Purely right column
            right_parts.append(stripped)
        else:
            # May have both columns, or left only
            left_part, right_part = split_at_gap(line.lstrip(' '))
            if left_part:
                left_parts.append(left_part)
            if right_part:
                right_parts.append(right_part)

    left_text  = ' '.join(p for p in left_parts  if p)
    right_text = ' '.join(p for p in right_parts if p)
    return code, left_text, right_text


def split_objectives(right_text_lines_str):
    """
    Split a concatenated right-column string into individual Learning Objectives.
    Uses heuristic: new objective when previous ends with non-continuation word
    AND next line starts with an OBJ_VERB.
    """
    # Work line by line (split back on the joins we did)
    # Since we joined with spaces, re-split might lose structure.
    # Instead, keep raw lines and process them.
    pass  # handled inline in parse_l_entry


def split_objective_lines(right_parts):
    """
    Given a list of raw right-column line strings, group them into
    individual objective strings.
    """
    if not right_parts:
        return []

    objectives = []
    current = []

    for line in right_parts:
        s = line.strip()
        if not s:
            continue
        if current:
            last_word = ' '.join(current).split()[-1].lower().rstrip('.,;:()')
            first_word = s.split()[0].lower().rstrip('.,;:()')
            if last_word not in CONT_ENDS and first_word in OBJ_VERBS:
                objectives.append(' '.join(current))
                current = [s]
            else:
                current.append(s)
        else:
            current.append(s)

    if current:
        objectives.append(' '.join(current))
    return objectives


def parse_p_entry(lines):
    """Return (code, pc_text, eoa_text)."""
    code, left, right = parse_two_col_block(lines, CODE_P_RE)
    return code, left, right


def parse_l_entry(lines):
    """Return (code, lo_text, [objective_strings])."""
    first = lines[0]
    m = CODE_L_RE.match(first)
    code = m.group(1)
    code_end = m.start(2)

    rest_of_first = first[code_end:]
    left_start, right_start = split_at_gap(rest_of_first)
    right_abs = find_right_col_start(first, code_end)

    lo_parts    = [left_start]  if left_start  else []
    right_parts = [right_start] if right_start else []

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        leading = len(line) - len(line.lstrip(' '))

        if right_abs and leading >= right_abs - 4:
            right_parts.append(stripped)
        else:
            left_part, right_part = split_at_gap(line.lstrip(' '))
            if left_part:
                lo_parts.append(left_part)
            if right_part:
                right_parts.append(right_part)

    lo_text = ' '.join(p for p in lo_parts if p)
    objectives = split_objective_lines(right_parts)
    return code, lo_text, objectives


def parse_range_lines(lines):
    """
    Convert raw RANGE OF VARIABLES text lines into a list of item strings.
    Each item starts with '<keyword> include[s]:'.
    """
    items = []
    current = []

    for line in lines:
        s = line.strip()
        if not s:
            if current:
                items.append(' '.join(current))
                current = []
            continue

        # Detect start of a new item: contains 'include' or 'includes' + ':'
        if re.match(r'^\S.*\binclude[sd]?\s*:', s, re.IGNORECASE) and current:
            items.append(' '.join(current))
            current = [s]
        elif not current:
            current = [s]
        else:
            current.append(s)

    if current:
        items.append(' '.join(current))

    return items


# ── Main conversion ─────────────────────────────────────────────────────────────

def is_skip_line(line):
    """True for lines we want to drop (jurisdiction tables, column headers)."""
    return (PROVINCE_RE.search(line) or
            YESNV_RE.match(line) or
            PC_HDR_RE.search(line) or
            LO_HDR_RE.search(line))


def collect_entry_block(lines, start):
    """Collect all lines for one code entry starting at lines[start]."""
    block = [lines[start]]
    i = start + 1
    while i < len(lines):
        ln = lines[i]
        if (CODE_P_RE.match(ln) or CODE_L_RE.match(ln) or
                RANGE_RE.match(ln) or SKILLS_RE.match(ln) or
                KNOWLEDGE_RE.match(ln) or SUBTASK_RE.match(ln) or
                TASK_RE.match(ln) or MAJOR_RE.match(ln)):
            break
        block.append(ln)
        i += 1
    return block, i


def collect_range_block(lines, start):
    """Collect raw text lines of a RANGE OF VARIABLES section."""
    raw = []
    i = start + 1
    while i < len(lines):
        ln = lines[i]
        if (CODE_P_RE.match(ln) or CODE_L_RE.match(ln) or
                RANGE_RE.match(ln) or SKILLS_RE.match(ln) or
                KNOWLEDGE_RE.match(ln) or SUBTASK_RE.match(ln) or
                TASK_RE.match(ln) or MAJOR_RE.match(ln)):
            break
        if ln.strip():
            raw.append(ln.strip())
        i += 1
    return raw, i


def convert(text):
    lines = text.splitlines()
    out = []
    i = 0

    major_letter = ''
    current_task_title = ''
    first_subtask = True

    while i < len(lines):
        ln = lines[i]

        # ── Skip noise lines ────────────────────────────────────────────────
        if is_skip_line(ln) or not ln.strip():
            i += 1
            continue

        # ── MAJOR WORK ACTIVITY ─────────────────────────────────────────────
        m = MAJOR_RE.match(ln)
        if m:
            major_letter = m.group(1)
            # Next non-blank line is the description
            i += 1
            desc = ''
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and not TASK_RE.match(lines[i]):
                desc = lines[i].strip()
                i += 1
            out.append(f'MAJOR WORK ACTIVITY {major_letter}')
            if desc:
                out.append(desc)
            out.append('')
            first_subtask = True
            continue

        # ── TASK ────────────────────────────────────────────────────────────
        m = TASK_RE.match(ln)
        if m:
            task_code  = m.group(1)
            task_title = m.group(2).strip()
            out.append(f'TASK {task_code} | {task_title}')
            i += 1
            # Consume TASK DESCRIPTOR label then collect paragraph
            if i < len(lines) and TASKDESC_RE.match(lines[i]):
                i += 1
            # Gather descriptor lines
            desc_parts = []
            while i < len(lines):
                candidate = lines[i]
                if (SUBTASK_RE.match(candidate) or TASK_RE.match(candidate) or
                        MAJOR_RE.match(candidate) or is_skip_line(candidate)):
                    break
                if candidate.strip():
                    desc_parts.append(candidate.strip())
                elif desc_parts:
                    break
                i += 1
            if desc_parts:
                out.append(' '.join(desc_parts))
            out.append('')
            out.append('SUB-TASKS:')
            out.append('')
            first_subtask = True
            continue

        # ── SUB-TASK ────────────────────────────────────────────────────────
        m = SUBTASK_RE.match(ln)
        if m:
            sub_code  = m.group(1)
            sub_title = m.group(2).strip()
            out.append(f'SUB-TASK {sub_code} | {sub_title}')
            out.append('')
            i += 1
            continue

        # ── SKILLS / KNOWLEDGE sections ─────────────────────────────────────
        if SKILLS_RE.match(ln):
            out.append('SKILLS:')
            out.append('')
            i += 1
            continue

        if KNOWLEDGE_RE.match(ln):
            out.append('KNOWLEDGE:')
            out.append('')
            i += 1
            continue

        # ── RANGE OF VARIABLES ───────────────────────────────────────────────
        if RANGE_RE.match(ln):
            raw, i = collect_range_block(lines, i)
            items = parse_range_lines(raw)
            out.append('RANGE OF VARIABLES:')
            for item in items:
                out.append(f'- {item}')
            out.append('')
            continue

        # ── Performance (P) code ─────────────────────────────────────────────
        if CODE_P_RE.match(ln):
            block, i = collect_entry_block(lines, i)
            code, pc, eoa = parse_p_entry(block)
            out.append(f'- {code}')
            out.append(f'  Performance Criteria: {pc}')
            out.append(f'  Evidence of Attainment: {eoa}')
            out.append('')
            continue

        # ── Learning (L) code ────────────────────────────────────────────────
        if CODE_L_RE.match(ln):
            block, i = collect_entry_block(lines, i)
            code, lo, objectives = parse_l_entry(block)
            out.append(f'- {code}')
            out.append(f'  Learning Outcomes: {lo}')
            out.append('  Learning Objectives:')
            for obj in objectives:
                out.append(f'  - {obj}')
            out.append('')
            continue

        # ── Anything else (task descriptor overflow, etc.) ───────────────────
        i += 1

    # Clean up: collapse 3+ blank lines to 2
    result = []
    blank_count = 0
    for ln in out:
        if ln == '':
            blank_count += 1
            if blank_count <= 1:
                result.append(ln)
        else:
            blank_count = 0
            result.append(ln)

    return '\n'.join(result).strip() + '\n'


def main():
    src_dir = Path('txt-source')
    v1_files = sorted(src_dir.glob('*-cleaned-v1.txt'))

    if not v1_files:
        print('No *-cleaned-v1.txt files found in txt-source/')
        return

    for src in v1_files:
        letter = src.stem.split('-')[0]
        dst = src_dir / f'{letter}-cleaned-v2.txt'

        if dst.exists():
            print(f'Skipping {letter} (already exists)')
            continue

        print(f'Converting {letter}...')
        text = src.read_text(encoding='utf-8')
        result = convert(text)
        dst.write_text(result, encoding='utf-8')
        print(f'  -> {dst.name}')


if __name__ == '__main__':
    main()
