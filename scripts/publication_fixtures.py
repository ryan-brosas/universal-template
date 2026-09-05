"""Shared isolation and unconditional checks for publication CLI fixtures."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def fixture_environment(root: Path) -> dict[str, str]:
    """Keep fixture Git operations independent of host config and outer repos."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CEILING_DIRECTORIES": str(root.parent.resolve()),
    })
    return env


def fixture_git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=",
         "-c", "init.templateDir=", "-c", "user.name=Fixture",
         "-c", "user.email=fixture@example.invalid", *args],
        cwd=root, env=fixture_environment(root), check=True,
    )


def verify_fixture_support() -> None:
    """Guard host-config isolation, outer Git discovery and optimized checks."""
    with tempfile.TemporaryDirectory(prefix="fixture-isolation-") as temp:
        outer = Path(temp)
        fixture_git(outer, "init", "-q")
        root = outer / "nested"
        root.mkdir()
        config = outer / "host.gitconfig"
        config.write_text(
            "[core]\n autocrlf = true\n safecrlf = true\n"
            "[commit]\n gpgsign = true\n", encoding="utf-8",
        )
        (root / "mixed.md").write_bytes(b"first\r\nsecond\n")
        hostile = {"GIT_CONFIG_GLOBAL": str(config), "GIT_DIR": str(outer / ".git"),
                   "GIT_WORK_TREE": str(outer)}
        with patch.dict(os.environ, hostile):
            fixture_git(root, "init", "-q")
            fixture_git(root, "add", ".")
            fixture_git(root, "commit", "-qm", "fixture")
            env = fixture_environment(root)
        blob = subprocess.run(["git", "show", "HEAD:mixed.md"], cwd=root,
                              env=env, capture_output=True, check=True)
        require(blob.stdout == b"first\r\nsecond\n", "fixture Git transformed bytes")
        # An empty sibling must not accidentally discover the outer repository.
        empty = outer / "empty"
        empty.mkdir()
        discovery = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=empty,
                                   env=fixture_environment(empty), capture_output=True)
        require(discovery.returncode != 0, "fixture discovered an outer repository")
        optimized = subprocess.run(
            [sys.executable, "-O", "-c",
             "from publication_fixtures import require; require(False, 'injected failure')"],
            cwd=Path(__file__).parent, env=env, capture_output=True, text=True,
        )
        require(optimized.returncode != 0 and "injected failure" in optimized.stderr,
                "optimized Python disabled the fixture check")


def require(condition: bool, message: str) -> None:
    """Unlike assert, execute the condition and fail even under python -O."""
    if not condition:
        raise AssertionError(message)
