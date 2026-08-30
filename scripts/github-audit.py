#!/usr/bin/env python3
"""github-audit.py - READ-ONLY drift audit of remote GitHub state.

Compares the repository's intended GitHub surface (local .github files, label
taxonomy consumers, workflows) against the actual remote configuration, and
reports per-surface facts. Never mutates anything: audit -> report; mutation
happens only through an authorized setup session (github-repo-setup).

Intentional omissions are declared in KNOWN_INTENTIONAL so repeated audits
stay quiet about decisions already made; anything else reported as a GAP is a
candidate for setup. Run from the repository root with `gh` authenticated.

Usage:
  python3 scripts/github-audit.py            # human report
  python3 scripts/github-audit.py --strict   # exit 1 on unexpected gaps
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPO_ENV = "GITHUB_AUDIT_REPO"

# Deliberate omissions for THIS repository (the decision log; see the
# github-repo-setup full-setup report). Audit output stays quiet about these.
KNOWN_INTENTIONAL = {
    "homepage": "no canonical site exists",
    "wiki": "documentation lives in version-controlled files",
    "projects": "no project-management workflow is in use",
    "discussions": "solo repository; no community conversation volume yet",
    "merge queue": "solo repository with low PR volume",
    "codeowners": "solo repository; no ownership split to encode",
    "social preview": "manual upload via the settings UI; API path not used",
}

issues: list[str] = []  # unexpected gaps (strict mode)


def sh(args: list[str]) -> tuple[int, str]:
    p = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout + p.stderr).strip()


def repo_slug() -> str:
    rc, out = sh(["git", "remote", "get-url", "origin"])
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", out)
    if rc != 0 or not m:
        print("FATAL: no github origin found")
        sys.exit(2)
    return m.group(1)


def api(path: str) -> tuple[int, str]:
    path = path.strip("/")
    url = f"repos/{REPO}/{path}" if path else f"repos/{REPO}"
    return sh(["gh", "api", url])


def section(title: str) -> None:
    print(f"\n== {title} ==")


def fact(name: str, detail: str) -> None:
    print(f"  OK   {name}: {detail}")


def gap(name: str, detail: str, key: str | None = None) -> None:
    key = key or name
    reason = KNOWN_INTENTIONAL.get(key)
    if reason:
        print(f"  SKIP {name}: {reason}")
    else:
        print(f"  GAP  {name}: {detail}")
        issues.append(f"{name}: {detail}")


def needs_decision(name: str, detail: str) -> None:
    print(f"  DECIDE {name}: {detail}")
    issues.append(f"{name}: {detail} (needs decision)")


def repo_json() -> dict:
    rc, out = api("")
    if rc != 0:
        print(f"FATAL: cannot read repository: {out[:200]}")
        sys.exit(2)
    return json.loads(out)


def audit() -> None:
    global REPO
    REPO = os.environ.get(REPO_ENV) or repo_slug()
    print(f"GitHub drift audit (read-only) for {REPO}")
    r = repo_json()

    section("Identity")
    desc = r.get("description") or ""
    if desc:
        fact("description", desc)
    else:
        gap("description", "empty")
    if r.get("homepage"):
        fact("homepage", r["homepage"])
    else:
        gap("homepage", "not set", key="homepage")
    topics = r.get("topics") or []
    if topics:
        fact("topics", f"{len(topics)}: {', '.join(topics)}")
    else:
        gap("topics", "none configured")
    if r.get("license"):
        fact("license", r["license"].get("spdx_id") or "?")
    else:
        needs_decision("license", "no LICENSE file on a public repository")

    section("Collaboration features")
    for key, label in (("has_issues", "issues"), ("has_projects", "projects"),
                       ("has_discussions", "discussions"), ("has_wiki", "wiki")):
        state = "enabled" if r.get(key) else "disabled"
        if r.get(key) and label in ("projects", "discussions", "wiki") and label not in KNOWN_INTENTIONAL:
            gap(label, f"feature flag on; confirm it is used", key=label)
        else:
            fact(label, state)

    section("Merge policy")
    fact("merge methods", f"merge={r.get('allow_merge_commit')} squash={r.get('allow_squash_merge')} rebase={r.get('allow_rebase_merge')}")
    if r.get("allow_auto_merge"):
        fact("auto-merge capability", "enabled (activation stays per-PR, user-authorized)")
    else:
        gap("auto-merge capability", "disabled")
    if r.get("allow_update_branch"):
        fact("update branch", "enabled")
    else:
        gap("update branch", "disabled")
    if r.get("delete_branch_on_merge"):
        fact("delete branch on merge", "enabled")
    else:
        print("  INFO delete branch on merge: disabled (existing merged branches are preserved by convention)")

    section("Labels vs automation consumers")
    rc, out = sh(["gh", "label", "list", "--limit", "1000", "--json", "name"])
    remote_labels = {x["name"] for x in json.loads(out)} if rc == 0 else set()
    if remote_labels:
        fact("remote labels", f"{len(remote_labels)} configured")
    else:
        gap("labels", "none configured")
    required: set[str] = set()
    for path, pat in ((BASE / ".github/labeler.yml", r"^([^#\s][^:]*):\s*$"),
                      (BASE / ".github/release.yml", r"^\s*-\s+['\"]?([A-Za-z0-9:_*-]+)['\"]?\s*$")):
        if path.is_file():
            for line in path.read_text().splitlines():
                m = re.match(pat, line)
                if m:
                    name = m.group(1).strip("\"'")
                    if name not in ("changelog", "exclude", "categories", "labels", "title") and not name.startswith("-"):
                        required.add(name)
    for form in sorted((BASE / ".github/ISSUE_TEMPLATE").glob("*.yml")) if (BASE / ".github/ISSUE_TEMPLATE").is_dir() else []:
        for m in re.finditer(r"labels:\s*\[([^\]]+)\]", form.read_text()):
            required.update(x.strip().strip('"\'') for x in m.group(1).split(","))
    for dep in (BASE / ".github/dependabot.yml",):
        if dep.is_file():
            for m in re.finditer(r"^\s+-\s+(type:[a-z]+|breaking-change|release:skip)\s*$", dep.read_text(), re.M):
                required.add(m.group(1))
    required = {x for x in required if ":" in x or x in ("breaking-change", "release:skip")}
    missing = sorted(required - remote_labels)
    if missing:
        gap("labels referenced by automation", f"missing on remote: {missing}")
    elif required:
        fact("automation-referenced labels", f"all {len(required)} present on remote")

    section("Templates and community files")
    for rel in (".github/pull_request_template.md", ".github/ISSUE_TEMPLATE", ".github/release.yml",
                ".github/dependabot.yml", "SECURITY.md", "CONTRIBUTING.md", "CODEOWNERS",
                "CODE_OF_CONDUCT.md", "SUPPORT.md"):
        p = BASE / rel
        present = p.is_file() or p.is_dir()
        print(f"  {'OK  ' if present else 'SKIP'} {rel}: {'present' if present else 'absent'}")

    section("Governance (rulesets)")
    rc, out = api("rulesets")
    rulesets = json.loads(out) if rc == 0 and out.strip() else []
    if rulesets:
        for rs in rulesets:
            fact("ruleset", f"{rs['name']} ({rs['enforcement']})")
        rc2, out2 = api(f"rulesets/{rulesets[0]['id']}")
        if rc2 == 0:
            for rule in json.loads(out2).get("rules", []):
                if rule["type"] == "required_status_checks":
                    names = [c["context"] for c in rule["parameters"].get("required_status_checks", [])]
                    fact("required checks", ", ".join(names) if names else "none")
    else:
        gap("rulesets", "none configured (default branch unprotected)")

    section("Security")
    for path, label, enabled_words in (
        ("vulnerability-alerts", "dependabot alerts", None),
        ("automated-security-fixes", "dependabot security updates", None),
        ("private-vulnerability-reporting", "private vulnerability reporting", None),
    ):
        rc, out = api(path)
        if rc == 0:
            try:
                data = json.loads(out)
                state = "enabled" if data.get("enabled", True) else "disabled"
            except json.JSONDecodeError:
                state = "enabled" if rc == 200 else "disabled"
            (fact if state == "enabled" else gap)(label, state)
        else:
            gap(label, f"unavailable or disabled (gh exit {rc})")
    sas = r.get("security_and_analysis") or {}
    for key, label in (("secret_scanning", "secret scanning"),
                       ("secret_scanning_push_protection", "push protection"),
                       ("secret_scanning_non_provider_patterns", "non-provider patterns"),
                       ("dependabot_security_updates", "dependabot security updates")):
        status = (sas.get(key) or {}).get("status", "unknown")
        (fact if status == "enabled" else gap)(label, status)
    rc, out = api("code-scanning/default-setup")
    if rc == 0:
        state = json.loads(out).get("state", "unknown")
        (fact if state == "configured" else gap)("code scanning default setup", state)
    else:
        print(f"  INFO code scanning default setup: not readable ({rc})")

    section("Dependencies")
    dep = BASE / ".github/dependabot.yml"
    if dep.is_file():
        text = dep.read_text()
        ecosystems = re.findall(r"package-ecosystem:\s*(\S+)", text)
        fact("dependabot", f"ecosystems: {ecosystems}")
        if "github-actions" not in ecosystems and list(BASE.glob('.github/workflows/*.yml')):
            gap("dependabot github-actions", "SHA-pinned actions without update automation")
    else:
        gap("dependabot", "no .github/dependabot.yml")
    for wf in sorted((BASE / ".github/workflows").glob("*.yml")):
        for i, line in enumerate(wf.read_text().splitlines(), 1):
            m = re.search(r"pip install\s+--user\s+([a-zA-Z0-9_.-]+)\s*$", line)
            if m:
                gap("pinned CI tool", f"{wf.name}:{i}: unpinned 'pip install --user {m.group(1)}'", key="ci-tool-pin")

    section("Releases")
    rc, out = api("tags?per_page=100")
    tags = json.loads(out) if rc == 0 else []
    rc, out = api("releases?per_page=100")
    releases = json.loads(out) if rc == 0 else []
    fact("tags/releases", f"{len(tags)} tags, {len(releases)} releases")
    has_release_yml = (BASE / ".github/release.yml").is_file()
    print(f"  {'OK  ' if has_release_yml else 'SKIP'} .github/release.yml: {'present' if has_release_yml else 'absent'}")
    print("  INFO immutable releases: verify in Settings > Releases (not exposed for read via this API path)")

    print()
    if issues:
        print(f"AUDIT: {len(issues)} unexpected gap(s)")
        for x in issues:
            print(f"  - {x}")
        if "--strict" in sys.argv:
            sys.exit(1)
    else:
        print("AUDIT: no unexpected gaps")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    audit()
