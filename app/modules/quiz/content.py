"""Bounded text-only snapshots of the user's learning material."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(value)
    return " ".join(re.sub(r"data:[^\s]+", "", " ".join(parser.parts)).split())


def build_snapshot(groups: list[list[dict]], budget: int) -> list[dict]:
    """Round-robin categories, deduplicate text, and bound serialized input."""
    sources: list[dict] = []
    seen: set[str] = set()
    used = 2
    for position in range(max((len(group) for group in groups), default=0)):
        for group in groups:
            if position >= len(group):
                continue
            row = group[position]
            content = plain_text(row["content"])[:1600]
            key = content.casefold()
            if len(content) < 8 or not any(c.isalpha() for c in content) or key in seen:
                continue
            source = {**row, "title": plain_text(row["title"])[:180], "content": content}
            size = len(json.dumps(source, ensure_ascii=False)) + 2
            if used + size > budget:
                continue
            seen.add(key)
            sources.append(source)
            used += size
    return sources
