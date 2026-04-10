"""Markdown to Telegram HTML conversion."""
from __future__ import annotations

import html as html_module
import re

TG_MAX_LEN = 4096


def md_to_html(text: str) -> str:
    """Convert Markdown to Telegram-safe HTML.

    Handles code blocks, headers, tables, horizontal rules, lists,
    and inline formatting (bold, italic, underline, inline code, links).
    """
    # 1. Stash fenced code blocks before escaping
    code_blocks: list[str] = []

    def _stash_code(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = html_module.escape(m.group(2))
        if lang:
            code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
        else:
            code_blocks.append(f"<pre><code>{code}</code></pre>")
        return f"\x00CODE{len(code_blocks) - 1}\x00"

    text = re.sub(r"```(\w*)\n?(.*?)```", _stash_code, text, flags=re.DOTALL)

    # 2. Escape remaining HTML
    text = html_module.escape(text)

    # 3. Block-level elements
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("\x00CODE") and stripped.endswith("\x00"):
            out.append(code_blocks[int(stripped[5:-1])])
            i += 1
            continue

        hdr = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hdr:
            out.append(f"\n<b>{hdr.group(2)}</b>\n")
            i += 1
            continue

        if re.match(r"^[-*_]{3,}\s*$", stripped):
            out.append("")
            i += 1
            continue

        if "|" in stripped and stripped.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if re.match(r"^\|[\s\-:|]+\|$", row):
                    i += 1
                    continue
                table_lines.append(row)
                i += 1
            if table_lines:
                out.append("<pre>" + "\n".join(table_lines) + "</pre>")
            continue

        li = re.match(r"^(\s*)[-*+]\s+(.+)$", stripped)
        if li:
            out.append(f"  \u2022 {li.group(2)}")
            i += 1
            continue

        oli = re.match(r"^(\s*)\d+[.)]\s+(.+)$", stripped)
        if oli:
            out.append(f"  {stripped}")
            i += 1
            continue

        out.append(line)
        i += 1

    text = "\n".join(out)

    # 4. Inline formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<u>\1</u>", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # 5. Clean up excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
