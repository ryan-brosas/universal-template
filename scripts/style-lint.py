#!/usr/bin/env python3
"""style-lint.py - deterministic house-style checks for authored prose.

House style: STE-inspired plain technical English with project-specific
spoken-style constraints (skills/house-writing-style/). This is NOT formal
ASD-STE100 compliance and must not be described as such.

Layers:
- HARD rules (ERROR): high-confidence lexical/structural violations
- SOFT rules (WARN): heuristics for review; never fail CI

Protected spans are never linted: fenced code blocks, inline code, blockquotes
(quotation fidelity), YAML frontmatter, link URLs, and raw HTML tags. Style
applies to natural-language prose the agent authors.

Usage:
  python3 scripts/style-lint.py [files-or-dirs...]   # default: built-in docs scope
  python3 scripts/style-lint.py --selftest           # fixture assertions
  python3 scripts/style-lint.py --format json ...    # machine-readable

Exit 1 when any ERROR; warnings never fail.
Zero dependencies; python3 stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# --- rule tables -----------------------------------------------------------
# (rule id, regex, level, message template)
HARD_RULES = [
    ("em-dash", re.compile("\u2014"), "ERROR", "em dash in prose"),
    ("filler-intensifier",
     re.compile(r"\b(genuinely|really|truly|actually)\b", re.I), "ERROR",
     "filler intensifier"),
    ("banned-word",
     re.compile(r"\b(utilize|utilizing|utilizes|seamlessly|effortlessly|delve|"
                r"delving|game-changer|game-changing|supercharge|supercharges)\b",
                re.I),
     "ERROR", "slop word"),
    ("throat-clearing",
     re.compile(r"^\s*(it is important to note|it should be noted|it's worth noting)\b",
                re.I), "ERROR", "throat-clearing opener"),
    ("artificial-landing",
     re.compile(r"^\s*(in conclusion|to summarize|in summary|all in all|"
                r"at the end of the day)\b", re.I),
     "ERROR", "artificial landing sentence"),
    ("decorative-separator", re.compile(r"^\s*([=\-_])\1{5,}\s*$"), "ERROR",
     "decorative separator line"),
]

SOFT_RULES = [
    ("corporate-verb", re.compile(r"\b(leverage|underscore)\b", re.I), "WARN",
     "corporate-register verb (check context; keep technical use)"),
    ("negative-parallelism", re.compile(r"\bnot only\b", re.I), "WARN",
     "possible rhetorical negative parallelism (technical contrast is fine)"),
]

LONG_SENTENCE_WORDS = 45
LONG_PARAGRAPH_WORDS = 120
CADENCE_MIN_SENTENCES = 6
CADENCE_MAX_SPREAD = 3

INLINE_CODE = re.compile(r"`[^`\n]+`")
URL = re.compile(r"https?://[^\s)>\]]+")
HTML_TAG = re.compile(r"</?[a-zA-Z][^>\n]*>")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
LIST_PREFIX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _mask(line: str) -> str:
    """Blank protected spans (inline code, URLs, raw HTML), preserving length."""
    for pat in (INLINE_CODE, URL, HTML_TAG):
        line = pat.sub(lambda m: "\x00" * len(m.group(0)), line)
    return line


def lint_text(text: str, name: str = "<text>") -> list[dict]:
    """Lint one Markdown document; returns violations (file, line, col, level, rule, message)."""
    lines = text.splitlines()
    out: list[dict] = []

    # Skip YAML frontmatter.
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break

    fenced = False
    sentence_starts: list[str] = []   # consecutive sentence first-words
    para_counts: list[int] = []       # words per sentence in current paragraph
    cadence_reported = False

    def flush_paragraph() -> None:
        nonlocal cadence_reported
        if len(para_counts) >= CADENCE_MIN_SENTENCES and not cadence_reported:
            spread = max(para_counts) - min(para_counts)
            if spread <= CADENCE_MAX_SPREAD:
                out.append({"file": name, "line": line_no, "col": 1, "level": "WARN",
                            "rule": "uniform-cadence",
                            "message": f"uniform sentence cadence (spread {spread} words; mix short and medium)"})
                cadence_reported = True
        para_counts.clear()

    line_no = 0
    for raw in lines[start:]:
        line_no += 1
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fenced = not fenced
            flush_paragraph()
            sentence_starts.clear()
            continue
        if fenced:
            continue
        if not stripped:
            flush_paragraph()
            sentence_starts.clear()
            continue
        if stripped.startswith(">"):
            continue  # blockquote: quotation fidelity
        if stripped.startswith("|"):
            para_counts.clear()
            sentence_starts.clear()
            continue  # markdown table row: structured data, protected
        masked = _mask(raw)

        # HARD rules
        for rule, pat, level, msg in HARD_RULES:
            m = pat.search(masked)
            if m:
                out.append({"file": name, "line": line_no, "col": m.start() + 1,
                            "level": level, "rule": rule, "message": msg})

        # SOFT lexical rules
        for rule, pat, level, msg in SOFT_RULES:
            m = pat.search(masked)
            if m:
                out.append({"file": name, "line": line_no, "col": m.start() + 1,
                            "level": level, "rule": rule, "message": msg})

        # A list item starts its own block: a 12-item list is not one paragraph,
        # and consecutive bullets must not read as one repeated-start paragraph.
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", stripped):
            para_counts.clear()
            sentence_starts.clear()

        # Sentence-level heuristics on masked prose
        prose = masked.replace("\x00", " ")
        sentences = [s for s in SENTENCE_SPLIT.split(prose) if s.strip()]
        for s in sentences:
            words = s.split()
            n_words = len(words)
            if n_words > LONG_SENTENCE_WORDS:
                out.append({"file": name, "line": line_no, "col": 1, "level": "WARN",
                            "rule": "long-sentence",
                            "message": f"sentence has {n_words} words (> {LONG_SENTENCE_WORDS})"})
            para_counts.append(n_words)
            first = re.sub(LIST_PREFIX, "", s).strip().split()
            sentence_starts.append(first[0].lower() if first else "")
        if len(sentence_starts) >= 3 and len({sentence_starts[-1]}) == 1 \
                and sentence_starts[-1] and len(sentence_starts[-1]) > 2 \
                and all(w == sentence_starts[-1] for w in sentence_starts[-3:]):
            out.append({"file": name, "line": line_no, "col": 1, "level": "WARN",
                        "rule": "repeated-sentence-start",
                        "message": f"3+ consecutive sentences start with {sentence_starts[-1]!r}"})
            sentence_starts.clear()
        if sum(para_counts) > LONG_PARAGRAPH_WORDS:
            out.append({"file": name, "line": line_no, "col": 1, "level": "WARN",
                        "rule": "long-paragraph",
                        "message": f"paragraph exceeds {LONG_PARAGRAPH_WORDS} words on one block"})
            para_counts.clear()

    flush_paragraph()
    return out


def iter_scope(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*.md")))
        elif p.is_file() and p.suffix == ".md":
            files.append(p)
    return files


def default_scope() -> list[Path]:
    return [
        BASE / "AGENTS.md",
        BASE / "README.md",
        BASE / "docs",
        BASE / "skills" / "house-writing-style",
    ]


def selftest() -> int:
    fx = BASE / "scripts" / "fixtures" / "style-lint"
    cases = [
        ("bad.md", {"em-dash", "filler-intensifier", "banned-word", "throat-clearing",
                    "artificial-landing", "decorative-separator"}),
        ("good.md", set()),
        ("protected.md", set()),
    ]
    ok = True
    for fname, want_error_rules in cases:
        p = fx / fname
        if not p.is_file():
            print(f"FAIL {fname}: fixture missing")
            ok = False
            continue
        v = lint_text(p.read_text(encoding="utf-8"), fname)
        err_rules = {x["rule"] for x in v if x["level"] == "ERROR"}
        if err_rules != want_error_rules:
            print(f"FAIL {fname}: expected ERROR rules {sorted(want_error_rules)}, got {sorted(err_rules)}")
            ok = False
        else:
            print(f"PASS {fname}: ERROR rules {sorted(err_rules) if err_rules else 'none'}")
    print("style-lint selftest: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="files or directories (default: docs scope)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    targets = [Path(a) for a in args.paths] or default_scope()
    violations: list[dict] = []
    for f in iter_scope(targets):
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        violations.extend(lint_text(text, str(f.relative_to(BASE)) if f.is_relative_to(BASE) else str(f)))

    if args.format == "json":
        print(json.dumps(violations, indent=2))
    else:
        for v in violations:
            print(f"{v['file']}:{v['line']}:{v['col']} {v['level']} {v['rule']}: {v['message']}")
        errors = [v for v in violations if v["level"] == "ERROR"]
        warns = [v for v in violations if v["level"] == "WARN"]
        print(f"style-lint: {len(errors)} errors, {len(warns)} warnings"
              + ("" if not violations else " (errors fail; warnings are review notes)"))
    sys.exit(1 if any(v["level"] == "ERROR" for v in violations) else 0)


if __name__ == "__main__":
    main()
