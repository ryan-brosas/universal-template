#!/usr/bin/env python3
"""skill-validator.py — mechanical format gate for ~/.agents/skills.

Canonical format (see templates/): practice/tool skills -> templates/skill.md
skeleton.

Severity: P0 = broken discovery/contract, P1 = retrieval or parity risk,
          P2 = style deviation from the mandated skeleton.
Zero dependencies. Exit 1 if any P0, else 0.
"""
import importlib.util
import os, re, sys
from pathlib import Path

try:
    # scripts/style-lint.py has a hyphen: import by file path, not module name.

    _spec = importlib.util.spec_from_file_location(
        "style_lint", str(Path(__file__).with_name("style-lint.py")))
    assert _spec is not None and _spec.loader is not None
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    lint_text = _mod.lint_text
except Exception:  # noqa: BLE001
    lint_text = None

try:
    # One canonical frontmatter parser: catalog-quality.py owns it.
    _cq_spec = importlib.util.spec_from_file_location(
        "catalog_quality", str(Path(__file__).with_name("catalog-quality.py")))
    assert _cq_spec is not None and _cq_spec.loader is not None
    _cq = importlib.util.module_from_spec(_cq_spec)
    _cq_spec.loader.exec_module(_cq)
    _parse_fm = _cq.parse_frontmatter
except Exception:  # noqa: BLE001
    _parse_fm = None

_REPO_SKILLS = str(Path(__file__).resolve().parents[1] / "skills")
ROOT = os.environ.get("SKILLS_ROOT", _REPO_SKILLS)

PRACTICE_SECTIONS = [
    ("Core Principle", "core principle"),
    ("When to Use / NOT", "when to use"),
    ("Workflow", "workflow"),
    ("Red Flags", "red flag"),
    ("Verification", "verification"),
    ("References", "references"),
]

def parse_frontmatter(text):
    """Return (fm dict, body) using the canonical catalog parser.

    catalog-quality.py owns frontmatter parsing; this wrapper recovers the
    body after the closing delimiter. Falls back to an inline parser only if
    catalog-quality cannot be imported.
    """
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text  # no closing delimiter: unparseable
    body = text[end + 4:]
    if _parse_fm is not None:
        fm = _parse_fm(text)
        if not fm:
            return None, text  # closing delimiter but no parseable keys
        return fm, body
    lines = text[4:end].splitlines() if text.startswith("---\n") else text[3:end].splitlines()
    fm = {}
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        j = i + 1
        extra = []
        while j < len(lines) and not re.match(r"^[A-Za-z0-9_-]+:\s*", lines[j]):
            extra.append(lines[j])
            j += 1
        val = " ".join([val] + [e.strip() for e in extra]).strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
        i = j
    return fm, body

def headings(body):
    return [h.strip().lower() for h in re.findall(r"^#{1,6}\s+(.+)$", body, re.M)]

def check_sections(body, spec):
    hs = headings(body)
    missing = []
    for label, needle in spec:
        if not any(needle in h for h in hs):
            missing.append(label)
    return missing

def ref_lines(body):
    return re.findall(r"^\s*-\s+`references/([^`]+)`", body, re.M)


def main():
    report = []
    counts = {"P0": 0, "P1": 0, "P2": 0}
    n_practice = 0
    for d in sorted(os.listdir(ROOT)):
        dpath = os.path.join(ROOT, d)
        if not os.path.isdir(dpath):
            continue
        if d.startswith("."):
            continue  # e.g. .system — Codex host bundle, not a catalog skill leaf
        skill_md = os.path.join(dpath, "SKILL.md")
        issues = []
        if not os.path.isfile(skill_md):
            issues.append(("P0", "SKILL.md missing"))
            report.append((d, issues))
            counts["P0"] += 1
            continue
        text = open(skill_md, encoding="utf-8").read()
        fm, body = parse_frontmatter(text)
        if fm is None:
            issues.append(("P0", "frontmatter unparseable"))
            report.append((d, issues))
            counts["P0"] += 1
            continue
        if fm.get("name") != d:
            issues.append(("P0", f"name '{fm.get('name')}' != folder '{d}'"))
        desc = fm.get("description", "")
        if not desc:
            issues.append(("P0", "description missing"))
        elif len(desc) > 1024:
            issues.append(("P0", f"description {len(desc)} chars > 1024"))
        if desc and not desc.lower().startswith("use when"):
            issues.append(("P1", "description does not start with 'Use when'"))
        # Archived cold libraries (x-archive: true) are content, not
        # procedures: the filesystem is their index, so the skeleton and
        # orphan-reference style checks do not apply.
        archived = str(fm.get("x-archive", "")).strip().lower() == "true"
        refs_dir = os.path.join(dpath, "references")
        disk_refs = set()
        if os.path.isdir(refs_dir):
            disk_refs = {f for f in os.listdir(refs_dir) if f.endswith(".md")}
        cited = ref_lines(body)
        cited_set = set(cited)
        for c in sorted(cited_set):
            if c not in disk_refs:
                issues.append(("P1", f"cited reference missing on disk: {c}"))
        if not archived:
            for o in sorted(disk_refs - cited_set):
                issues.append(("P2", f"orphan reference not cited in SKILL.md: {o}"))
        n_practice += 1
        if not archived:
            for label in check_sections(body, PRACTICE_SECTIONS):
                issues.append(("P2", f"skeleton section missing: {label}"))
        if lint_text is not None:
            for v in lint_text(body)[:3]:
                issues.append(("P2", f"style[{v['level']}] {v['rule']}: {v['message']}"))
        for sev, _ in issues:
            counts[sev] += 1
        report.append((d, issues))
    # markdown report
    out = ["# Skill catalog audit", f"root: {ROOT}", f"practice/tool skills: {n_practice}",
           f"P0={counts['P0']} P1={counts['P1']} P2={counts['P2']}", "",
           "## P0/P1 offenders", ""]
    for d, issues in report:
        bad = [(s, m) for s, m in issues if s in ("P0", "P1")]
        if bad:
            out.append(f"### {d}")
            for s, m in bad:
                out.append(f"- [{s}] {m}")
            out.append("")
    out += ["## P2-only deviations (style)", ""]
    for d, issues in report:
        p2 = [m for s, m in issues if s == "P2"]
        if p2 and not any(s in ("P0", "P1") for s, _ in issues):
            out.append(f"- {d}: " + "; ".join(p2))
    txt = "\n".join(out) + "\n"
    dest = os.environ.get("AUDIT_OUT", "/tmp/skill-audit-report.md")
    open(dest, "w", encoding="utf-8").write(txt)
    print(f"skills scanned: {len(report)} (practice {n_practice})")
    print(f"P0={counts['P0']} P1={counts['P1']} P2={counts['P2']}")
    print(f"report: {dest}")
    sys.exit(1 if counts["P0"] else 0)

if __name__ == "__main__":
    main()
