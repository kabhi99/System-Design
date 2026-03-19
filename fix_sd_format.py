#!/usr/bin/env python3
"""
Fix formatting in System Design notes to match the standard style:
- Title: ALL CAPS with topic in parentheses
- Sections: ## SECTION N: TITLE (ALL CAPS)
- No --- horizontal rules between sections
- Bullets: * instead of - inside boxes
- Consistent box width (73 chars inner)
- Subtitle line after title
"""

import os
import re
import sys


def fix_title(lines):
    """Fix the title line to be ALL CAPS with proper format."""
    if not lines:
        return lines

    result = list(lines)

    # Find the first # line
    for i, line in enumerate(result):
        stripped = line.strip()
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title_text = stripped[2:].strip()
            # Already ALL CAPS? Skip
            if title_text == title_text.upper():
                break
            # Convert to ALL CAPS
            result[i] = '# ' + title_text.upper()
            break

    return result


def fix_section_headers(lines):
    """Convert ## N. Title to ## SECTION N: TITLE format."""
    result = []
    section_counter = 0

    for line in lines:
        stripped = line.strip()

        # Match ## N. Title or ## N: Title patterns
        m = re.match(r'^##\s+(\d+)\.\s+(.+)$', stripped)
        if not m:
            m = re.match(r'^##\s+(\d+):\s+(.+)$', stripped)

        if m:
            num = m.group(1)
            title = m.group(2).strip().upper()
            result.append(f'## SECTION {num}: {title}')
            continue

        # Match ## Summary or ## Full System Diagram etc (unnumbered sections)
        if re.match(r'^##\s+[A-Z]', stripped) and not stripped.startswith('## SECTION'):
            title = stripped[3:].strip().upper()
            result.append(f'## {title}')
            continue

        result.append(line)

    return result


def fix_subsection_headers(lines):
    """Convert ### Title Case to ### TITLE CASE."""
    result = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('### '):
            title = stripped[4:].strip()
            # Don't touch Q&A question headers (### Q1: ...)
            if re.match(r'^Q\d+:', title):
                result.append(line)
                continue
            result.append('### ' + title.upper())
            continue

        result.append(line)

    return result


def remove_hr_lines(lines):
    """Remove --- horizontal rule lines (standalone)."""
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped == '---':
            continue
        result.append(line)
    return result


def fix_bullets_in_boxes(lines):
    """Convert - bullets to * bullets inside code blocks (ASCII boxes)."""
    result = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            # Inside a code block, convert - bullets to * bullets
            # But only if the line starts with |  ... -  (inside a box)
            converted = re.sub(r'^(\|[\s]*[\s]*)- ', r'\1* ', line)
            if converted == line:
                # Also handle non-box code blocks with - bullets
                converted = re.sub(r'^(\s+)- ', r'\1* ', line)
            result.append(converted)
        else:
            result.append(line)

    return result


def fix_subtitle(lines):
    """Ensure subtitle line exists after title."""
    if len(lines) < 2:
        return lines

    result = list(lines)

    # Find title line
    title_idx = None
    for i, line in enumerate(result):
        if line.strip().startswith('# ') and not line.strip().startswith('## '):
            title_idx = i
            break

    if title_idx is None:
        return result

    # Check if next non-empty line is the italic subtitle
    next_idx = title_idx + 1
    while next_idx < len(result) and not result[next_idx].strip():
        next_idx += 1

    if next_idx < len(result):
        next_line = result[next_idx].strip()
        # If next line is already a subtitle (*...*)
        if next_line.startswith('*') and next_line.endswith('*') and not next_line.startswith('**'):
            pass  # already has subtitle
        elif next_line.startswith('## ') or next_line.startswith('```'):
            # Missing subtitle - add a generic one
            result.insert(title_idx + 1, '')
            result.insert(title_idx + 2, '*Complete Design: Requirements, Architecture, and Interview Guide*')

    return result


def add_section_prefix(lines):
    """Add SECTION prefix to ## headers that don't have it."""
    result = []
    section_num = 0

    for line in lines:
        stripped = line.strip()

        # Already has SECTION prefix
        if re.match(r'^## SECTION \d+:', stripped):
            m = re.match(r'^## SECTION (\d+):', stripped)
            section_num = int(m.group(1))
            result.append(line)
            continue

        # ## HEADER without SECTION prefix (but not special ones)
        if (stripped.startswith('## ') and
            not stripped.startswith('## SECTION') and
            not stripped.startswith('## END') and
            not stripped.startswith('## ARCHITECTURE')):

            title = stripped[3:].strip()
            # Skip if it looks like a sub-topic reference
            if title and title[0].isalpha():
                section_num += 1
                result.append(f'## SECTION {section_num}: {title}')
                continue

        result.append(line)

    return result


def clean_multiple_blanks(lines):
    """Remove consecutive blank lines (keep max 1)."""
    result = []
    prev_blank = False
    for line in lines:
        if not line.strip():
            if not prev_blank:
                result.append(line)
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False
    return result


def process_file(path):
    """Process a single .md file."""
    with open(path, 'r') as f:
        content = f.read()

    lines = content.split('\n')

    # Apply fixes in order
    lines = fix_title(lines)
    lines = fix_subtitle(lines)
    lines = remove_hr_lines(lines)
    lines = fix_section_headers(lines)
    lines = fix_subsection_headers(lines)
    lines = add_section_prefix(lines)
    lines = fix_bullets_in_boxes(lines)
    lines = clean_multiple_blanks(lines)

    result = '\n'.join(lines)

    with open(path, 'w') as f:
        f.write(result)

    print(f'  Fixed: {os.path.basename(os.path.dirname(path))}/{os.path.basename(path)} ({len(lines)} lines)')


def main():
    base = '/Users/akush4/personal/System Design/md/Notes-Detailed'

    # Files that need formatting fixes
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        'Google-Maps',
        'S3-Object-Storage',
        'Unique-ID-Generator',
        'Metrics-Monitoring',
    ]

    for folder in targets:
        path = os.path.join(base, folder, '01-Complete-Design.md')
        if os.path.exists(path):
            process_file(path)
        else:
            print(f'  SKIP (not found): {folder}')

    print('\nDone!')


if __name__ == '__main__':
    main()
