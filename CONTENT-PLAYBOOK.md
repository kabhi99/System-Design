# Content Playbook: Adding & Updating System Design Notes

Standard process for adding new content, updating existing notes, fixing formatting, and pushing changes.

## Step 1: Content Standards

### File Structure

Every system design note follows this layout:

```
# TOPIC NAME IN ALL CAPS
*Complete Design: Requirements, Architecture, and Interview Guide*

Brief 2-3 line description of the system.

## SECTION 1: UNDERSTANDING THE PROBLEM

### SUBSECTION TITLE

(content in ASCII boxes inside code fences)

## SECTION 2: NEXT TOPIC
...
```

### Rules

| Rule | Example |
|------|---------|
| Title | `# CHAT SYSTEM DESIGN (WHATSAPP / SLACK)` — ALL CAPS |
| Subtitle | `*Complete Design: Requirements, ...*` — italic, line 2 |
| Sections | `## SECTION N: TITLE` — ALL CAPS, numbered |
| Subsections | `### SUBSECTION TITLE` — ALL CAPS |
| Bullets inside boxes | Use `*` not `-` |
| No horizontal rules | Never use `---` between sections |
| Max 1 consecutive blank line | No double blank lines |

### ASCII Box Format

All content goes inside code-fenced ASCII boxes. Standard width is **75 chars** per line (outer `|` at position 0 and position 74):

```
+-------------------------------------------------------------------------+    <- 75 chars total
|                                                                         |    <- 73 chars inner
|  Content here, indented 2 spaces from the left border                   |
|                                                                         |
+-------------------------------------------------------------------------+
```

Key rules:
- Every line in a code block must be the **same width** (typically 75 chars)
- Content is indented 2 spaces from the left `|`
- Right padding fills the gap between content and the closing `|`
- Nested inner boxes must align their `|` with their `+---+` borders

### Technology Justifications (WHY blocks)

Whenever a technology is mentioned (Redis, PostgreSQL, Kafka, Elasticsearch, etc.), add a **WHY** justification at the same place. Format:

```
|  STORAGE: Redis (primary) + PostgreSQL (backup)                         |
|  * WHY REDIS? Cart is accessed on every page view. Sub-ms reads.       |
|    Hash structure maps naturally to cart:{user_id}. TTL auto-cleans    |
|    abandoned carts without cleanup jobs.                                |
|  * WHY POSTGRESQL BACKUP? Redis is volatile. Async write-behind        |
|    ensures cart survives Redis failures. Needed for analytics.         |
```

WHY justifications should be:
- **Concise**: 2-4 lines max per technology
- **Specific**: mention actual properties (sub-ms, TTL, ACID, inverted index)
- **Comparative**: say why NOT the alternative ("SQL LIKE scans full table")
- **Quantified** where possible: latency, throughput, storage size

## Step 2: Make Your Content Changes

1. Open the target `.md` file
2. Add/update content following the standards above
3. Ensure every tech choice has a WHY justification
4. Keep ASCII box lines at consistent width within each code block

## Step 3: Fix Formatting

### 3a. Run `fix_sd_format.py`

This script fixes headers, bullets, blank lines, and section numbering.

```bash
cd "/Users/akush4/personal/System Design"

# Single folder (pass the folder name, NOT the file path):
python3 fix_sd_format.py FolderName

# Multiple folders:
python3 fix_sd_format.py E-Commerce Chat-System Proximity-Service

# Examples:
python3 fix_sd_format.py Proximity-Service
python3 fix_sd_format.py Food-Delivery-App
```

What it fixes:
- Title -> ALL CAPS
- `## N. Title` -> `## SECTION N: TITLE`
- `### title` -> `### TITLE`
- `-` bullets -> `*` bullets inside code blocks
- Removes `---` horizontal rules
- Removes consecutive blank lines
- Adds subtitle if missing

**Note**: The script looks for `01-Complete-Design.md` inside the folder. For files with different names (e.g., `02-High-Level-Architecture.md`), you need to either modify the script or fix those manually.

### 3b. Fix Box Width Alignment

After editing content, lines may end up with inconsistent widths. Run this Python snippet to normalize all code block lines to the same width within each block:

```bash
cd "/Users/akush4/personal/System Design"

python3 << 'PYEOF'
import sys

filepath = sys.argv[1]  # pass the file path

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
            # Too short — add spaces before trailing |
            lines[idx] = line[:-1] + (' ' * diff) + '|\n'
            fixed += 1
        elif diff < 0:
            # Too long — remove trailing spaces before |
            content = line[:-1]
            trailing = len(content) - len(content.rstrip(' '))
            remove = min(-diff, trailing)
            if remove > 0:
                lines[idx] = content[:-remove] + '|\n'
                fixed += 1

with open(filepath, 'w') as f:
    f.writelines(lines)

print(f'Fixed {fixed} lines in {filepath}')
PYEOF
```

Usage:

```bash
# Fix a single file:
python3 fix_box_width.py md/Notes-Detailed/Proximity-Service/01-Complete-Design.md

# Fix multiple files:
for f in md/Notes-Detailed/E-Commerce/*.md; do python3 fix_box_width.py "$f"; done
```

### 3c. Unicode Sanitization (if needed)

If the file has unicode box-drawing characters (from copy-paste), use the mapping from `format_txt_to_md.py` to replace them:

| Unicode | ASCII |
|---------|-------|
| `│ ║` | `\|` |
| `─ ═ ━` | `-` `=` `-` |
| `┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼` | `+` |
| `→ ←` | `> <` |
| `•` | `*` |
| `— –` | `-` |

Run `format_txt_to_md.py` for bulk conversion, or manually replace characters.

## Step 4: Verify

Quick check — run this to confirm zero width issues:

```bash
python3 -c "
with open('PATH_TO_FILE') as f:
    lines = f.readlines()
in_code = False
issues = 0
for i, line in enumerate(lines):
    s = line.rstrip('\n')
    if s.startswith('\`\`\`'):
        if not in_code:
            in_code = True; bl = []
        else:
            in_code = False
            if bl:
                ws = {}
                for idx in bl:
                    w = len(lines[idx].rstrip('\n'))
                    if w > 0: ws[w] = ws.get(w, 0) + 1
                if ws:
                    t = max(ws, key=ws.get)
                    for idx in bl:
                        w = len(lines[idx].rstrip('\n'))
                        if w != t and w > 0 and lines[idx].strip():
                            issues += 1
                            print(f'  Line {idx+1}: {w} vs {t}')
        continue
    if in_code: bl.append(i)
print(f'Issues: {issues}')
"
```

Expected output: `Issues: 0`

## Step 5: Commit and Push

```bash
cd "/Users/akush4/personal/System Design"

git add -A
git status --short          # review what's staged
git commit -m "Your commit message here"
git push
```

Commit message conventions:
- `Add X section in Y notes` — new content
- `Expand X section with detailed coverage` — significantly more content
- `Add WHY justifications for tech choices in X` — technology reasoning
- `Fix box formatting in X` — width/alignment fixes

## Quick Reference: Full Workflow

```bash
# 1. Edit your files

# 2. Format
python3 fix_sd_format.py FolderName
python3 fix_box_width.py md/Notes-Detailed/FolderName/01-Complete-Design.md

# 3. Verify
python3 -c "..." # (verification snippet above)

# 4. Push
git add -A && git commit -m "message" && git push
```
