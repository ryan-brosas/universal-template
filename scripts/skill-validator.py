#!/usr/bin/env python3
"""skill-validator.py — mechanical format gate for ~/.agents/skills.

Two canonical formats (see templates/):
  A. practice/tool skills  -> templates/skill.md skeleton
  B. foundation leaves     -> templates/foundation-skill.md skeleton
     (detected by directory name ending in "-foundation")

Severity: P0 = broken discovery/contract, P1 = retrieval or parity risk,
          P2 = style deviation from the mandated skeleton.
Zero dependencies. Exit 1 if any P0, else 0.
"""
import os, re, sys
from pathlib import Path

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
FOUNDATION_SECTIONS = [
    ("Use this for", "use this for"),
    ("Capsule map", "capsule map"),
    ("Provenance", "provenance"),
    ("Full view", "full view"),
    ("Boundaries", "boundaries"),
]

def parse_frontmatter(text):
    """Return (fm dict, body). fm values may be multi-line YAML scalars."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    raw = text[4:end] if text.startswith("---\n") else text[3:end]
    body = text[end + 4:]
    fm = {}
    lines = raw.splitlines()
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

def map_bullets(body):
    m = re.search(r"^#{1,6}\s+Capsule map\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if not m:
        return None
    return len(re.findall(r"^\s*-\s+\*\*", m.group(1), re.M))

def main():
    report = []
    counts = {"P0": 0, "P1": 0, "P2": 0}
    n_practice = n_found = 0
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
        refs_dir = os.path.join(dpath, "references")
        disk_refs = set()
        if os.path.isdir(refs_dir):
            disk_refs = {f for f in os.listdir(refs_dir) if f.endswith(".md")}
        cited = ref_lines(body)
        cited_set = set(cited)
        for c in sorted(cited_set):
            if c not in disk_refs:
                issues.append(("P1", f"cited reference missing on disk: {c}"))
        for o in sorted(disk_refs - cited_set):
            issues.append(("P2", f"orphan reference not cited in SKILL.md: {o}"))
        is_found = d.endswith("-foundation")
        if is_found:
            n_found += 1
            missing = check_sections(body, FOUNDATION_SECTIONS)
            for label in missing:
                issues.append(("P2", f"foundation section missing: {label}"))
            v2 = v1 = 0
            for f in sorted(disk_refs):
                t = open(os.path.join(refs_dir, f), encoding="utf-8").read()
                v2 += t.count("capsule-v2 -->")
                v1 += t.count("capsule-v1 -->")
            mb = map_bullets(body)
            if len(cited_set) != v2 + v1:
                issues.append(("P1", f"parity: {len(cited_set)} loader refs != {v2+v1} capsule markers ({v2} v2 / {v1} v1)"))
            if len(cited_set) > 0 and mb == 0:
                issues.append(("P1", "capsule map empty but loader refs exist"))
            # every loader ref must be named somewhere in the capsule map, in any
            # bullet style (top-level, grouped, or nested sub-bullets)
            mm = re.search(r"^#{1,6}\s+Capsule map\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S)
            if mm and len(cited_set) > 0:
                map_text = mm.group(1)
                for c in sorted(cited_set):
                    name = c[:-3]
                    if not re.search(r"\b" + re.escape(name) + r"\b", map_text):
                        issues.append(("P1", f"loader ref missing from capsule map: {name}"))
        else:
            n_practice += 1
            for label in check_sections(body, PRACTICE_SECTIONS):
                issues.append(("P2", f"skeleton section missing: {label}"))
        for sev, _ in issues:
            counts[sev] += 1
        report.append((d, issues))
    # markdown report
    out = ["# Skill catalog audit", f"root: {ROOT}", f"practice/tool skills: {n_practice}, foundation leaves: {n_found}",
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
    print(f"skills scanned: {len(report)} (practice {n_practice}, foundation {n_found})")
    print(f"P0={counts['P0']} P1={counts['P1']} P2={counts['P2']}")
    print(f"report: {dest}")
    sys.exit(1 if counts["P0"] else 0)

if __name__ == "__main__":
    main()
