"""
Split *-cleaned-v2.txt files into individual sub-task Markdown files.
Output: output/subtasks/{code}.md  (e.g. A-1.01.md, B-3.01.md)
"""
import re
from pathlib import Path

# ── Patterns ──────────────────────────────────────────────────────────────────
MAJOR_RE    = re.compile(r'^MAJOR WORK ACTIVITY ([A-Z])\s*$')
TASK_RE     = re.compile(r'^TASK ([A-Z]-\d+) \| (.+)$')
SUBTASK_RE  = re.compile(r'^SUB-TASK ([A-Z]-\d+\.\d{2}) \| (.+)$')
SUBTASKS_HDR= re.compile(r'^SUB-TASKS:\s*$')
SKILLS_RE   = re.compile(r'^SKILLS:\s*$')
KNOWLEDGE_RE= re.compile(r'^KNOWLEDGE:\s*$')
RANGE_RE    = re.compile(r'^RANGE OF VARIABLES:\s*$')
CODE_P_RE   = re.compile(r'^- ([A-Z]-\d+\.\d+\.\d+P)$')
CODE_L_RE   = re.compile(r'^- ([A-Z]-\d+\.\d+\.\d+L)$')
PC_RE       = re.compile(r'^\s{2}Performance Criteria: (.+)$')
EOA_RE      = re.compile(r'^\s{2}Evidence of Attainment: (.+)$')
LO_RE       = re.compile(r'^\s{2}Learning Outcomes: (.+)$')
LOBJ_HDR_RE = re.compile(r'^\s{2}Learning Objectives:\s*$')
LOBJ_RE     = re.compile(r'^\s{2}- (.+)$')
RANGE_ITM_RE= re.compile(r'^- (.+)$')


def render_subtask_md(subtask_code, subtask_title, task_code, task_title,
                      task_desc, major_letter, major_desc, blocks):
    """
    Render a single sub-task's content as Markdown.
    blocks = list of ('skills'|'range_skills'|'knowledge'|'range_knowledge', data)
    """
    lines = []

    # ── Header ─────────────────────────────────────────────────────────────────
    lines.append(f'# {subtask_code} | {subtask_title}')
    lines.append('')
    lines.append(f'**Major Work Activity:** {major_letter} — {major_desc}')
    lines.append(f'**Task:** {task_code} | {task_title}')
    lines.append('')

    for block_type, data in blocks:

        # ── Skills ──────────────────────────────────────────────────────────────
        if block_type == 'skills':
            lines.append('## Skills')
            lines.append('')
            for entry in data:
                code = entry['code']
                pc   = entry.get('pc', '')
                eoa  = entry.get('eoa', '')
                lines.append(f'### {code}')
                lines.append(f'**Performance Criteria:** {pc}')
                lines.append('')
                lines.append(f'**Evidence of Attainment:** {eoa}')
                lines.append('')

        # ── Range of Variables (Skills) ─────────────────────────────────────────
        elif block_type == 'range_skills':
            lines.append('## Range of Variables')
            lines.append('')
            for item in data:
                lines.append(f'- {item}')
            lines.append('')

        # ── Knowledge ───────────────────────────────────────────────────────────
        elif block_type == 'knowledge':
            lines.append('## Knowledge')
            lines.append('')
            for entry in data:
                code = entry['code']
                lo   = entry.get('lo', '')
                objs = entry.get('objectives', [])
                lines.append(f'### {code}')
                lines.append(f'**Learning Outcomes:** {lo}')
                lines.append('')
                if objs:
                    lines.append('**Learning Objectives:**')
                    for obj in objs:
                        lines.append(f'- {obj}')
                lines.append('')

        # ── Range of Variables (Knowledge) ──────────────────────────────────────
        elif block_type == 'range_knowledge':
            lines.append('## Range of Variables (Knowledge)')
            lines.append('')
            for item in data:
                lines.append(f'- {item}')
            lines.append('')

    # Strip trailing blank lines
    while lines and lines[-1] == '':
        lines.pop()

    return '\n'.join(lines) + '\n'


def parse_v2_file(text):
    """
    Parse a *-cleaned-v2.txt file and yield (subtask_code, subtask_title,
    task_code, task_title, task_desc, major_letter, major_desc, blocks) tuples.
    """
    lines = text.splitlines()
    n = len(lines)

    major_letter = ''
    major_desc   = ''
    task_code    = ''
    task_title   = ''
    task_desc    = ''

    i = 0
    while i < n:
        ln = lines[i]

        # ── MAJOR ────────────────────────────────────────────────────────────
        m = MAJOR_RE.match(ln)
        if m:
            major_letter = m.group(1)
            i += 1
            if i < n and lines[i].strip():
                major_desc = lines[i].strip()
                i += 1
            continue

        # ── TASK ─────────────────────────────────────────────────────────────
        m = TASK_RE.match(ln)
        if m:
            task_code  = m.group(1)
            task_title = m.group(2)
            i += 1
            # Next non-blank line is the descriptor
            while i < n and not lines[i].strip():
                i += 1
            if i < n and not SUBTASKS_HDR.match(lines[i]) and not SUBTASK_RE.match(lines[i]):
                task_desc = lines[i].strip()
                i += 1
            continue

        # ── SUB-TASK ─────────────────────────────────────────────────────────
        m = SUBTASK_RE.match(ln)
        if m:
            subtask_code  = m.group(1)
            subtask_title = m.group(2)
            i += 1

            blocks = []
            current_section = None   # 'skills' | 'range_skills' | 'knowledge' | 'range_knowledge'
            skill_entries = []
            knowledge_entries = []
            range_items = []
            current_entry = None     # dict being built
            seen_range = 0           # 0=none, 1=skills range done

            while i < n:
                ln2 = lines[i]

                # Stop at next SUB-TASK, TASK, or MAJOR
                if SUBTASK_RE.match(ln2) or TASK_RE.match(ln2) or MAJOR_RE.match(ln2):
                    break

                # ── Section headers ──────────────────────────────────────────
                if SKILLS_RE.match(ln2):
                    current_section = 'skills'
                    i += 1
                    continue

                if KNOWLEDGE_RE.match(ln2):
                    # Flush any open skill entry
                    if current_entry:
                        skill_entries.append(current_entry)
                        current_entry = None
                    if skill_entries:
                        blocks.append(('skills', skill_entries))
                        skill_entries = []
                    current_section = 'knowledge'
                    i += 1
                    continue

                if RANGE_RE.match(ln2):
                    # Flush open entry
                    if current_entry:
                        if current_section == 'skills':
                            skill_entries.append(current_entry)
                        else:
                            knowledge_entries.append(current_entry)
                        current_entry = None
                    # Flush collected entries
                    if skill_entries:
                        blocks.append(('skills', skill_entries))
                        skill_entries = []
                    if knowledge_entries:
                        blocks.append(('knowledge', knowledge_entries))
                        knowledge_entries = []
                    # Collect range items
                    range_items = []
                    i += 1
                    while i < n:
                        ln3 = lines[i]
                        if (SUBTASK_RE.match(ln3) or TASK_RE.match(ln3) or
                                MAJOR_RE.match(ln3) or SKILLS_RE.match(ln3) or
                                KNOWLEDGE_RE.match(ln3) or RANGE_RE.match(ln3)):
                            break
                        m3 = RANGE_ITM_RE.match(ln3)
                        if m3:
                            range_items.append(m3.group(1))
                        i += 1
                    range_type = 'range_skills' if seen_range == 0 else 'range_knowledge'
                    seen_range += 1
                    blocks.append((range_type, range_items))
                    continue

                # ── Skill entries ────────────────────────────────────────────
                if current_section == 'skills':
                    mp = CODE_P_RE.match(ln2)
                    if mp:
                        if current_entry:
                            skill_entries.append(current_entry)
                        current_entry = {'code': mp.group(1)}
                        i += 1
                        continue
                    if current_entry:
                        mpc = PC_RE.match(ln2)
                        if mpc:
                            current_entry['pc'] = mpc.group(1)
                            i += 1
                            continue
                        me = EOA_RE.match(ln2)
                        if me:
                            current_entry['eoa'] = me.group(1)
                            i += 1
                            continue

                # ── Knowledge entries ────────────────────────────────────────
                if current_section == 'knowledge':
                    ml = CODE_L_RE.match(ln2)
                    if ml:
                        if current_entry:
                            knowledge_entries.append(current_entry)
                        current_entry = {'code': ml.group(1), 'objectives': []}
                        i += 1
                        continue
                    if current_entry:
                        mlo = LO_RE.match(ln2)
                        if mlo:
                            current_entry['lo'] = mlo.group(1)
                            i += 1
                            continue
                        if LOBJ_HDR_RE.match(ln2):
                            i += 1
                            continue
                        mobj = LOBJ_RE.match(ln2)
                        if mobj:
                            current_entry['objectives'].append(mobj.group(1))
                            i += 1
                            continue

                i += 1

            # Flush remaining
            if current_entry:
                if current_section == 'skills':
                    skill_entries.append(current_entry)
                elif current_section == 'knowledge':
                    knowledge_entries.append(current_entry)
            if skill_entries:
                blocks.append(('skills', skill_entries))
            if knowledge_entries:
                blocks.append(('knowledge', knowledge_entries))

            yield (subtask_code, subtask_title, task_code, task_title,
                   task_desc, major_letter, major_desc, blocks)
            continue

        i += 1


def main():
    src_dir = Path('txt-source-v2')
    out_dir = Path('output/subtasks')
    out_dir.mkdir(parents=True, exist_ok=True)

    v2_files = sorted(src_dir.glob('*-cleaned-v2.txt'))
    if not v2_files:
        print('No *-cleaned-v2.txt files found in txt-source-v2/')
        return

    total = 0
    for src in v2_files:
        letter = src.stem.split('-')[0]
        text = src.read_text(encoding='utf-8')

        count = 0
        for (sub_code, sub_title, t_code, t_title, t_desc,
             maj_letter, maj_desc, blocks) in parse_v2_file(text):

            md = render_subtask_md(sub_code, sub_title, t_code, t_title,
                                   t_desc, maj_letter, maj_desc, blocks)
            out_path = out_dir / f'{sub_code}.md'
            out_path.write_text(md, encoding='utf-8')
            count += 1

        print(f'{letter}: {count} subtask files written')
        total += count

    print(f'\nTotal: {total} files → {out_dir}/')


if __name__ == '__main__':
    main()
