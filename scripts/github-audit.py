#!/usr/bin/env python3
"""Print a read-only snapshot of current GitHub repository configuration.

This optional diagnostic reports remote facts. It does not decide which GitHub
features a repository should enable or classify intentional omissions.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys


def run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=60, check=False)
    return result.returncode, (result.stdout or result.stderr).strip()


def repository() -> str:
    code, output = run(["git", "remote", "get-url", "origin"])
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", output)
    if code or not match:
        raise RuntimeError("no GitHub origin found")
    return match.group(1)


def api(repo: str, path: str = "") -> object:
    code, output = run(["gh", "api", f"repos/{repo}/{path}".rstrip("/")])
    if code:
        return {"available": False, "error": output[:300]}
    if not output:
        return {"available": True}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"available": True, "output": output}


def collect(repo: str) -> dict:
    root = api(repo)
    labels_code, labels_output = run(["gh", "label", "list", "--repo", repo, "--limit", "1000", "--json", "name"])
    workflows_code, workflows_output = run(["gh", "workflow", "list", "--repo", repo, "--json", "name,state,path"])
    return {
        "repository": repo,
        "identity": root,
        "rulesets": api(repo, "rulesets"),
        "vulnerability_alerts": api(repo, "vulnerability-alerts"),
        "private_vulnerability_reporting": api(repo, "private-vulnerability-reporting"),
        "code_scanning_default_setup": api(repo, "code-scanning/default-setup"),
        "labels": json.loads(labels_output) if labels_code == 0 else {"available": False, "error": labels_output[:300]},
        "workflows": json.loads(workflows_output) if workflows_code == 0 else {"available": False, "error": workflows_output[:300]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="OWNER/REPO; defaults to origin")
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.repo or repository()), indent=2))
    except (RuntimeError, subprocess.SubprocessError) as exc:
        print(f"github-audit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
