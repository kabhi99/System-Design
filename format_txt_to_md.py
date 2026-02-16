#!/usr/bin/env python3
"""
Convert plain-text system design notes to properly formatted Markdown.

Usage:
    # Convert a single file:
    python3 format_txt_to_md.py input.txt output.md

    # Convert all .txt files in a directory into md/ folder:
    python3 format_txt_to_md.py --all /path/to/notes

Handles:
    - ====== header blocks  ->  # / ## markdown headers
    - ────── underlines     ->  ### sub-headers
    - ASCII box drawings    ->  wrapped in code fences
    - Shell/code commands   ->  ```bash / ```yaml etc.
    - Indented bullet text  ->  de-indented markdown lists
    - Unicode chars         ->  pure ASCII (1:1 width) for alignment
    - Line width padding    ->  consistent widths in code blocks
"""

import os
import re
import sys
import glob

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

EQUALS_RE = re.compile(r'^\s*={10,}\s*$')
DASH_RE = re.compile(r'^\s*─{10,}\s*$')
DRAWING_CHARS = set('┌┐└┘│├┤┬┴┼═╔╗╚╝║╠╣╦╩╬')

# ---------------------------------------------------------------------------
# Unicode -> ASCII map (strict 1 char -> 1 char for alignment)
# ---------------------------------------------------------------------------

UNICODE_TO_ASCII = {
    # Box-drawing corners and junctions
    '┌': '+', '┐': '+', '└': '+', '┘': '+',
    '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
    '╔': '+', '╗': '+', '╚': '+', '╝': '+',
    '╠': '+', '╣': '+', '╦': '+', '╩': '+', '╬': '+',
    '╧': '+',
    # Box-drawing lines
    '│': '|', '║': '|',
    '─': '-', '═': '=', '━': '-',
    # Arrows
    '▼': 'v', '▲': '^',
    '►': '>', '◄': '<',
    '→': '>', '←': '<',
    '↑': '^', '↓': 'v',
    '↔': '-', '↩': '<', '↘': 'v',
    '╱': '/', '╲': '\\',
    # Bullets and checkmarks
    '•': '*', '✓': 'Y', '✗': 'X',
    # Block characters (used in diagrams)
    '█': '#', '▓': '#', '░': '.', '▄': '_', '▀': '-',
    # Geometric shapes
    '●': 'o', '○': 'o', '□': 'o', '■': '#',
    '☐': 'o', '∘': 'o', '⬡': 'o', '◌': 'o', '◯': 'o',
    '★': '*', '☆': '*', '◆': '*', '◇': '*', '▪': '*', '▫': '*',
    '▶': '>', '◀': '<', '▷': '>', '◁': '<',
    '△': '^', '▽': 'v',
    # Dashes and punctuation
    '—': '-', '–': '-',
    '×': 'x', '÷': '/',
    '≈': '~', '≠': '!', '≤': '<', '≥': '>',
    '±': '~', '∞': '~', '√': 'V',
    '°': 'o', '·': '.', '²': '2', '³': '3',
    '₹': 'R', '¢': 'c',
    # Greek letters
    'λ': 'A', 'σ': 's', 'κ': 'k', 'μ': 'u', 'µ': 'u', 'π': 'p',
    # Smart quotes
    '\u2018': "'", '\u2019': "'", '\u201C': '"', '\u201D': '"',
}

STRIP_EMOJIS = set([
    '\u2B50', '\U0001F4A5', '\u2705', '\u274C', '\U0001F4DA',
    '\U0001F3AF', '\U0001F50D', '\U0001F4A1', '\U0001F4CD',
    '\u26A0', '\uFE0F', '\u25CF',
])


def sanitize_unicode(text):
    """Replace all non-ASCII chars with ASCII equivalents."""
    for uc, asc in UNICODE_TO_ASCII.items():
        text = text.replace(uc, asc)
    for emoji in STRIP_EMOJIS:
        text = text.replace(emoji, '')
    result = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            continue
        result.append(ch)
    return ''.join(result)


# ---------------------------------------------------------------------------
# Code-block language detection
# ---------------------------------------------------------------------------

SHELL_PREFIXES = [
    '$', '#!', 'brew ', 'curl ', 'sudo ', 'apt ', 'apt-get ',
    'pip ', 'pip3 ', 'npm ', 'npx ', 'yarn ', 'pnpm ',
    'docker ', 'docker-compose ', 'kubectl ', 'minikube ',
    'helm ', 'git ', 'cd ', 'ls ', 'cat ', 'echo ', 'mkdir ',
    'cp ', 'mv ', 'rm ', 'wget ', 'tar ', 'chmod ', 'chown ',
    'export ', 'source ', 'ssh ', 'scp ', 'rsync ',
    'aws ', 'gcloud ', 'az ', 'terraform ',
    'python ', 'python3 ', 'java ', 'javac ', 'go ',
    'cargo ', 'make ', 'cmake ', 'gcc ',
    'vi ', 'vim ', 'nano ', 'touch ', 'grep ', 'sed ', 'awk ',
    'systemctl ', 'journalctl ', 'service ',
    'ping ', 'traceroute ', 'netstat ', 'ss ', 'ip ',
    'openssl ', 'base64 ',
]

YAML_STARTERS = [
    'apiVersion:', 'kind:', 'metadata:', 'spec:', 'containers:',
    'replicas:', 'selector:', 'template:', 'labels:', 'name:',
    'image:', 'ports:', 'resources:', 'limits:', 'requests:',
    'volumeMounts:', 'volumes:', 'env:', 'command:', 'args:',
    'services:', 'version:', 'networks:', 'deploy:',
]

DOCKERFILE_STARTERS = [
    'FROM ', 'RUN ', 'COPY ', 'ADD ', 'CMD ',
    'ENTRYPOINT ', 'EXPOSE ', 'ENV ', 'WORKDIR ',
    'VOLUME ', 'ARG ', 'LABEL ', 'HEALTHCHECK ',
]

SQL_STARTERS = [
    'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'CREATE ',
    'ALTER ', 'DROP ', 'TRUNCATE ', 'GRANT ', 'REVOKE ', 'WITH ',
]

CODE_STARTERS = [
    'func ', 'package ', 'import ', 'from ', 'class ',
    'def ', 'public ', 'private ', 'protected ', 'interface ',
    'const ', 'let ', 'var ', 'function ', 'async ',
    'if (', 'for (', 'while (', 'switch (', 'try {',
    'return ', 'throw ', 'new ', '@',
]


def block_looks_like_code(block_lines):
    for bl in block_lines:
        s = bl.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in SHELL_PREFIXES):
            return True
        if s.startswith('#') and not s.startswith('##'):
            return True
        if any(s.startswith(p) for p in YAML_STARTERS):
            return True
        if any(s.startswith(p) for p in DOCKERFILE_STARTERS):
            return True
        if any(s.startswith(p) for p in SQL_STARTERS):
            return True
        if any(s.startswith(p) for p in CODE_STARTERS):
            return True
        if s.startswith('{') or s.startswith('[') or s.endswith('{'):
            return True
    return False


def detect_lang(code_lines):
    for l in code_lines:
        s = l.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in SHELL_PREFIXES):
            return 'bash'
        if s.startswith('#') and not s.startswith('##'):
            return 'bash'
        if any(s.startswith(p) for p in YAML_STARTERS):
            return 'yaml'
        if any(s.startswith(p) for p in DOCKERFILE_STARTERS):
            return 'dockerfile'
        if any(s.startswith(p) for p in SQL_STARTERS):
            return 'sql'
        if s.startswith(('func ', 'package ')):
            return 'go'
        if s.startswith(('class ', 'def ', 'import ', 'from ')):
            return 'python'
        if s.startswith(('public ', 'private ', 'protected ', '@')):
            return 'java'
        if s.startswith(('const ', 'let ', 'var ', 'function ', 'async ')):
            return 'javascript'
    return ''


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def has_drawing(line):
    return any(c in DRAWING_CHARS for c in line)


def dedent_block(block):
    non_empty = [l for l in block if l.strip()]
    if not non_empty:
        return block
    min_ind = min(len(l) - len(l.lstrip()) for l in non_empty)
    return [l[min_ind:] if len(l) >= min_ind else l for l in block]


def trim_trailing(block):
    while block and not block[-1].strip():
        block.pop()
    return block


# ---------------------------------------------------------------------------
# Code-block padding (alignment fix)
# ---------------------------------------------------------------------------

def find_border_tail(line):
    """Scan from right to find where the nested border tail starts.

    Border tail = the rightmost sequence of border chars (| or +)
    each separated by 1-4 spaces.  E.g. '|  |  |' or '+  |' or '|'.
    Returns the start position, or -1 if none found.
    """
    i = len(line) - 1
    while i >= 0 and line[i] == ' ':
        i -= 1
    if i < 0 or line[i] not in '|+':
        return -1
    last_border = i
    i -= 1
    while i >= 0:
        spaces = 0
        while i >= 0 and line[i] == ' ':
            spaces += 1
            i -= 1
        if 1 <= spaces <= 4 and i >= 0 and line[i] in '|+':
            last_border = i
            i -= 1
        else:
            break
    return last_border


def pad_block(block):
    """Pad lines in a code block so right-side borders align consistently."""
    non_empty = [l for l in block if l.strip()]
    if not non_empty:
        return block
    max_len = max(len(l) for l in non_empty)
    result = []
    for l in block:
        if not l.strip() or len(l) >= max_len:
            result.append(l)
            continue
        diff = max_len - len(l)
        stripped = l.rstrip()
        tail_pos = find_border_tail(stripped)
        if tail_pos > 0:
            content = stripped[:tail_pos]
            tail = stripped[tail_pos:]
            if content.endswith(('-', '=')):
                result.append(content + '-' * diff + tail)
            else:
                result.append(content + ' ' * diff + tail)
        elif stripped.endswith('|'):
            result.append(stripped[:-1] + ' ' * diff + '|')
        elif stripped.endswith('+'):
            result.append(stripped[:-1] + '-' * diff + '+')
        else:
            result.append(l + ' ' * diff)
    return result


def normalize_code_blocks(text):
    """Find every code block and pad lines to consistent width."""
    lines = text.split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith('```'):
            out.append(line)
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            out.extend(pad_block(block))
            if i < n:
                out.append(lines[i])
                i += 1
        else:
            out.append(line)
            i += 1
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def convert(content):
    """Convert plain-text content to formatted Markdown."""
    lines = content.split('\n')
    out = []
    i = 0
    n = len(lines)
    first_header = True

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ── EQUALS HEADER ──
        if EQUALS_RE.match(stripped):
            i += 1
            parts = []
            while i < n and not EQUALS_RE.match(lines[i].strip()):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            if i < n:
                i += 1
            if parts:
                if first_header:
                    out.append(f'# {parts[0]}')
                    for p in parts[1:]:
                        out.append(f'*{p}*')
                    out.append('')
                    first_header = False
                else:
                    out.append(f'## {parts[0]}')
                    for p in parts[1:]:
                        out.append(f'*{p}*')
                    out.append('')
            continue

        # ── DASH UNDERLINE ──
        if DASH_RE.match(stripped):
            look = i + 1
            while look < n and not lines[look].strip():
                look += 1
            if look < n and not DASH_RE.match(lines[look].strip()) and not EQUALS_RE.match(lines[look].strip()):
                look2 = look + 1
                while look2 < n and not lines[look2].strip():
                    look2 += 1
                if look2 < n and DASH_RE.match(lines[look2].strip()):
                    out.append(f'### {lines[look].strip()}')
                    out.append('')
                    i = look2 + 1
                    continue
            j = len(out) - 1
            while j >= 0 and out[j].strip() == '':
                j -= 1
            if (j >= 0
                    and not out[j].startswith('#')
                    and not out[j].startswith('-')
                    and not out[j].startswith('*')
                    and not out[j].startswith('**')):
                out[j] = f'### {out[j].strip()}'
            i += 1
            if not out or out[-1] != '':
                out.append('')
            continue

        # ── ASCII ART / BOX ──
        if has_drawing(line) and not DASH_RE.match(stripped):
            block = [line]
            i += 1
            while i < n:
                l = lines[i]
                if has_drawing(l):
                    block.append(l)
                    i += 1
                elif l.strip() == '':
                    lk = i + 1
                    while lk < n and lines[lk].strip() == '':
                        lk += 1
                    if lk < n and has_drawing(lines[lk]):
                        block.append(l)
                        i += 1
                    else:
                        break
                elif l.startswith('    '):
                    block.append(l)
                    i += 1
                else:
                    break
            block = trim_trailing(block)
            block = dedent_block(block)
            out.append('```')
            out.extend(block)
            out.append('```')
            out.append('')
            continue

        # ── INDENTED BLOCK ──
        if line.startswith('    ') and stripped:
            block = [line]
            i += 1
            while i < n:
                l = lines[i]
                if l.startswith('    '):
                    block.append(l)
                    i += 1
                elif l.strip() == '':
                    if i + 1 < n and lines[i + 1].startswith('    '):
                        block.append(l)
                        i += 1
                    else:
                        break
                else:
                    break
            block = trim_trailing(block)

            if any(has_drawing(l) for l in block):
                block = dedent_block(block)
                out.append('```')
                out.extend(block)
                out.append('```')
                out.append('')
            elif block_looks_like_code(block):
                ded = [l[4:] if l.startswith('    ') else l for l in block]
                ded = trim_trailing(ded)
                lang = detect_lang(ded)
                out.append(f'```{lang}')
                out.extend(ded)
                out.append('```')
                out.append('')
            else:
                for bl in block:
                    out.append(bl.strip().replace('•', '-'))
                out.append('')
            continue

        # ── REGULAR LINE ──
        processed = stripped.replace('•', '-')
        if re.match(r'^[A-Z][A-Z\s&/\-,()]+:\s*$', processed) and len(processed) < 80:
            processed = f'**{processed.strip()}**'
        out.append(processed)
        i += 1

    # Clean multiple blanks
    result = []
    prev_blank = False
    for line in out:
        if line.strip() == '':
            if not prev_blank:
                result.append('')
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False

    final = '\n'.join(result) + '\n'
    sanitized = sanitize_unicode(final)
    return normalize_code_blocks(sanitized)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def convert_file(src, dst):
    """Convert a single .txt file to .md."""
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    md = convert(content)
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'  Done: {os.path.basename(dst)}')


def convert_all(base_dir):
    """Convert all .txt files under base_dir into md/ subfolder."""
    txt_files = sorted(glob.glob(os.path.join(base_dir, '**/*.txt'), recursive=True))
    md_dir = os.path.join(base_dir, 'md')
    print(f'Found {len(txt_files)} .txt files\n')
    for txt_path in txt_files:
        rel = os.path.relpath(txt_path, base_dir)
        md_rel = os.path.splitext(rel)[0] + '.md'
        md_path = os.path.join(md_dir, md_rel)
        convert_file(txt_path, md_path)
    print(f'\nConverted {len(txt_files)} files into {md_dir}/')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == '--all':
        base = sys.argv[2] if len(sys.argv) > 2 else '.'
        convert_all(base)
    elif len(sys.argv) == 3:
        convert_file(sys.argv[1], sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
