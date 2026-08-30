#!/usr/bin/env python3
"""foundation-search.py - find cold *-foundation skills by topic.

The foundation catalog is hidden from startup metadata (disable-model-invocation).
This is the mechanical discovery path: named prior-art gap -> ranked candidates.

Usage:
    python3 scripts/foundation-search.py "ASGI middleware" [--limit 5]

Source repositories come first: check <project>/reference/<repo>/ actual source
and tests before loading a foundation. Foundations are the cold fallback when
condensed procedural knowledge, a named historical edge case, or a capsule map
is cheaper than re-investigating.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "and", "or",
    "how", "does", "do", "is", "are", "our", "we", "my", "me", "use", "when",
}


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in STOPWORDS and len(t) > 1]


def capsule_names(body: str) -> list[str]:
    return re.findall(r"`?references/([a-z0-9-]+)\.md`?", body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--skills-root", default=str(BASE / "skills"))
    args = ap.parse_args()

    toks = tokens(args.query)
    if not toks:
        print("no searchable tokens in query", file=sys.stderr)
        return 2
    root = Path(args.skills_root)
    scored: list[tuple[float, str, list[str], list[str]]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not d.name.endswith("-foundation"):
            continue
        sm = d / "SKILL.md"
        if not sm.is_file():
            continue
        text = sm.read_text(encoding="utf-8", errors="ignore")
        low = text.lower()
        desc_start = low.find("description:")
        desc = low[desc_start:desc_start + 1400] if desc_start >= 0 else ""
        map_m = re.search(r"capsule map.*?(?=^#\s|\Z)", low, re.M | re.S)
        cmap = map_m.group(0) if map_m else ""
        score = 0.0
        matched: list[str] = []
        for t in toks:
            w = 0
            if t in d.name:
                w += 4
            w += 3 * cmap.count(t)
            w += 2 * desc.count(t)
            w += low.count(t)
            if w:
                matched.append(t)
                score += w
        if score:
            caps = [c for c in capsule_names(text)
                    if any(t in c for t in toks)]
            scored.append((score / math.sqrt(len(toks)), d.name, matched, caps))

    scored.sort(reverse=True)
    if not scored:
        print(f"no foundation matches for: {args.query}")
        return 0
    print(f"foundation candidates for: {args.query!r}")
    for score, name, matched, caps in scored[: args.limit]:
        cap_note = ("; capsules: " + ", ".join(caps[:4])) if caps else ""
        print(f"  {score:6.1f}  {name}  matched: {', '.join(matched)}{cap_note}")
    print("Load only the matching foundation (read its SKILL.md). "
          "Check <project>/reference/<repo> source first; foundations are the cold fallback.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
