#!/usr/bin/env python3
"""
Fix box width alignment in System Design .md files.

Normalizes all lines within each code block to the same width by adjusting
trailing padding before the closing |.

Usage:
    python3 fix_box_width.py FILE [FILE ...]
    python3 fix_box_width.py md/Notes-Detailed/Proximity-Service/01-Complete-Design.md
"""

import sys


def fix_file(filepath):
    with open(filepath) as f:
        lines = f.readlines()

    in_code = False
    code_blocks = []
    current_block = None

    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')
        if stripped.startswith('```'):
            if not in_code:
                in_code = True
                current_block = {'start': i, 'lines': []}
            else:
                in_code = False
                current_block['end'] = i
                code_blocks.append(current_block)
                current_block = None
            continue
        if in_code and current_block is not None:
            current_block['lines'].append(i)

    fixed = 0
    for block in code_blocks:
        widths = {}
        for idx in block['lines']:
            w = len(lines[idx].rstrip('\n'))
            if w > 0:
                widths[w] = widths.get(w, 0) + 1
        if not widths:
            continue
        target = max(widths, key=widths.get)

        for idx in block['lines']:
            line = lines[idx].rstrip('\n')
            w = len(line)
            if w == target or w == 0:
                continue
            if not (line.startswith('|') and line.endswith('|')):
                continue
            diff = target - w
            if diff > 0:
                lines[idx] = line[:-1] + (' ' * diff) + '|\n'
                fixed += 1
            elif diff < 0:
                content = line[:-1]
                trailing = len(content) - len(content.rstrip(' '))
                remove = min(-diff, trailing)
                if remove > 0:
                    lines[idx] = content[:-remove] + '|\n'
                    fixed += 1

    with open(filepath, 'w') as f:
        f.writelines(lines)

    print(f'  Fixed {fixed} lines in {filepath}')
    return fixed


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 fix_box_width.py FILE [FILE ...]')
        sys.exit(1)

    total = 0
    for filepath in sys.argv[1:]:
        total += fix_file(filepath)

    print(f'\nDone! {total} lines fixed across {len(sys.argv) - 1} file(s).')


if __name__ == '__main__':
    main()
