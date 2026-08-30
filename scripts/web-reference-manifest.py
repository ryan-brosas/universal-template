#!/usr/bin/env python3
"""web-reference-manifest.py - deterministic validation for web reference bundles.

A web reference lives at `<project>/reference/web/<site>/` and is produced by
the `web-reference` skill. This gate validates the machine-readable contract:
manifest fields, referenced evidence files, coverage-gap honesty, secret
hygiene, and the ADOPT/ADAPT/OMIT decision record. Subjective visual quality
is never validated mechanically.

Usage:
  python3 scripts/web-reference-manifest.py <bundle-dir> [more-dirs...]
  python3 scripts/web-reference-manifest.py --selftest

Exit 0 = no P0 findings (warnings allowed). Exit 1 = at least one P0.
Zero dependencies; python3 stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SCOPES = {"quick", "page", "site", "deep"}
MEDIA_REUSE = {"omit", "adapt", "reuse"}
MEDIA_REPLACEMENT = {"generate", "css", "svg", "none", ""}
EVIDENCE_KEYS = {
    "archive",
    "screenshots",
    "rendered_html",
    "source_html",
    "computed_styles",
    "css_variables",
    "interactions",
    "responsive",
}
MAX_SCAN_BYTES = 2 * 1024 * 1024
MAX_SCAN_FILES = 200
ARCHIVE_WARN_BYTES = 25 * 1024 * 1024

SECRET_PATTERNS = [
    ("openai-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer header", re.compile(r"(?i)authorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._-]+")),
    ("labeled secret", re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|password|auth[_-]?token)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}")),
]


class Findings:
    def __init__(self) -> None:
        self.p0: list[str] = []
        self.p1: list[str] = []

    def fail(self, msg: str) -> None:
        self.p0.append(msg)

    def warn(self, msg: str) -> None:
        self.p1.append(msg)


def iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def resolve_under(root: Path, rel: str) -> Path | None:
    """Resolve rel under root; None when absolute, escaping, or malformed."""
    if not isinstance(rel, str) or not rel or rel.startswith("/"):
        return None
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p


def check_path_ref(root: Path, rel: str, findings: Findings, where: str, allow_dir: bool = False) -> None:
    p = resolve_under(root, rel)
    if p is None:
        findings.fail(f"{where}: path escapes bundle or is not relative: {rel}")
        return
    if p.is_dir():
        if not allow_dir:
            findings.fail(f"{where}: expected a file, got a directory: {rel}")
        elif not any(p.iterdir()):
            findings.warn(f"{where}: page path has no captured files: {rel}")
        return
    if not p.is_file():
        findings.fail(f"{where}: referenced file missing: {rel}")
        return
    size = p.stat().st_size
    if size > ARCHIVE_WARN_BYTES:
        findings.warn(f"{where}: large file ({size // (1024 * 1024)}MB): {rel}; confirm the storage policy decision")


def check_file_ref(root: Path, rel: str, findings: Findings, where: str) -> None:
    check_path_ref(root, rel, findings, where, allow_dir=False)


def walk_text_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in {".md", ".json", ".txt"}:
            continue
        if p.stat().st_size > MAX_SCAN_BYTES:
            continue
        out.append(p)
        if len(out) >= MAX_SCAN_FILES:
            break
    return out


def scan_secrets(root: Path, findings: Findings) -> None:
    for p in walk_text_files(root):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.fail(f"{p.relative_to(root)}: credential-like material ({label}) must never be stored in a reference bundle")


def validate_bundle(raw_root: str) -> Findings:
    findings = Findings()
    root = Path(raw_root).resolve()
    if not root.is_dir():
        findings.fail(f"not a directory: {raw_root}")
        return findings

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        findings.fail("manifest.json missing")
        return findings
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.fail(f"manifest.json unreadable: {exc}")
        return findings

    if manifest.get("type") != "web-reference":
        findings.fail("manifest type must be 'web-reference'")

    source = manifest.get("source")
    parsed = urlparse(source) if isinstance(source, str) else None
    if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        findings.fail("manifest source must be an http(s) URL")

    captured_at = manifest.get("captured_at")
    if not isinstance(captured_at, str) or not iso8601(captured_at):
        findings.fail("manifest captured_at must be an ISO-8601 timestamp")

    scope = manifest.get("scope")
    if scope not in SCOPES:
        findings.fail(f"manifest scope must be one of {sorted(SCOPES)}")

    coverage = manifest.get("coverage_gaps", [])
    if not isinstance(coverage, list) or not all(isinstance(g, str) for g in coverage):
        findings.fail("coverage_gaps must be a list of strings")

    evidence = manifest.get("evidence", {})
    if not isinstance(evidence, dict):
        findings.fail("evidence must be an object")
        evidence = {}
    any_false = False
    for key, value in evidence.items():
        if key not in EVIDENCE_KEYS:
            findings.warn(f"evidence.{key} is not a known evidence key")
        if value is False:
            any_false = True
        elif isinstance(value, str):
            check_file_ref(root, value, findings, f"evidence.{key}")

    if any_false and not manifest.get("coverage_gaps"):
        findings.fail("evidence marked false but coverage_gaps is empty: a partial capture must be declared")

    pages = manifest.get("pages", [])
    if not isinstance(pages, list):
        findings.fail("pages must be a list")
        pages = []
    routes: set[str] = set()
    for i, page in enumerate(pages):
        if not isinstance(page, dict) or not isinstance(page.get("route"), str) or not page["route"]:
            findings.fail(f"pages[{i}] needs a route string")
            continue
        route = page["route"]
        if route in routes:
            findings.warn(f"duplicate route in pages: {route}")
        routes.add(route)
        path = page.get("path")
        if path is not None:
            check_path_ref(root, path, findings, f"pages[{i}].path", allow_dir=True)
        shots = page.get("screenshots", [])
        if isinstance(shots, list):
            for j, shot in enumerate(shots):
                check_file_ref(root, shot, findings, f"pages[{i}].screenshots[{j}]")
        else:
            findings.fail(f"pages[{i}].screenshots must be a list")
    if scope in {"site", "deep"} and not pages:
        findings.warn("site/deep capture lists no routes")

    viewports = manifest.get("viewports", [])
    if not isinstance(viewports, list) or not all(isinstance(v, str) for v in viewports):
        findings.fail("viewports must be a list of strings")
    elif scope in {"site", "deep"} and not viewports:
        findings.warn("site/deep capture declares no viewports")

    captures = manifest.get("captures", [])
    if not isinstance(captures, list):
        findings.fail("captures must be a list")
        captures = []
    dates: set[str] = set()
    for i, cap in enumerate(captures):
        if not isinstance(cap, dict) or not isinstance(cap.get("date"), str):
            findings.fail(f"captures[{i}] needs a date string")
            continue
        if cap["date"] in dates:
            findings.fail(f"duplicate capture date: {cap['date']}")
        dates.add(cap["date"])
        archive = cap.get("archive")
        if archive is not None:
            check_file_ref(root, archive, findings, f"captures[{i}].archive")

    media = manifest.get("media", [])
    if not isinstance(media, list):
        findings.fail("media must be a list")
        media = []
    for i, item in enumerate(media):
        if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not item["role"]:
            findings.fail(f"media[{i}] needs a role string")
            continue
        if item.get("reuse") not in MEDIA_REUSE:
            findings.fail(f"media[{i}].reuse must be one of {sorted(MEDIA_REUSE)}")
        if item.get("replacement", "none") not in MEDIA_REPLACEMENT:
            findings.warn(f"media[{i}].replacement is not a known replacement kind")

    reference_md = root / "REFERENCE.md"
    if not reference_md.is_file():
        findings.fail("REFERENCE.md missing")
    else:
        text = reference_md.read_text(encoding="utf-8", errors="replace")
        for token in ("ADOPT", "ADAPT", "OMIT"):
            if token not in text:
                findings.fail(f"REFERENCE.md missing {token} decision section")

    scan_secrets(root, findings)
    return findings


GOOD_REFERENCE = (
    "# Website Reference\n\n## ADOPT\n\nType scale.\n\n## ADAPT\n\nNav density.\n\n"
    "## OMIT\n\nBrand colors.\n"
)


def write_fixture(root: Path, manifest: str) -> None:
    (root / "captures" / "2026-08-31" / "raw").mkdir(parents=True, exist_ok=True)
    (root / "captures" / "2026-08-31" / "pages" / "home").mkdir(parents=True, exist_ok=True)
    (root / "captures" / "2026-08-31" / "screenshots").mkdir(parents=True, exist_ok=True)
    (root / "captures" / "2026-08-31" / "raw" / "site.wacz").write_bytes(b"WACZ")
    (root / "captures" / "2026-08-31" / "pages" / "home" / "rendered.html").write_text("<html></html>\n", encoding="utf-8")
    (root / "captures" / "2026-08-31" / "screenshots" / "home-desktop.png").write_bytes(b"png")
    (root / "REFERENCE.md").write_text(GOOD_REFERENCE, encoding="utf-8")
    (root / "manifest.json").write_text(manifest, encoding="utf-8")


def selftest() -> int:
    ok = True
    # Built from parts so this source file never contains a credential-like literal.
    fixture_key = "sk-" + "a" * 22
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        good = base / "good"
        write_fixture(good, json.dumps({
            "type": "web-reference",
            "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z",
            "scope": "site",
            "viewports": ["desktop", "mobile"],
            "pages": [{"route": "/", "path": "captures/2026-08-31/pages/home",
                       "screenshots": ["captures/2026-08-31/screenshots/home-desktop.png"]}],
            "evidence": {"archive": "captures/2026-08-31/raw/site.wacz", "screenshots": True,
                         "rendered_html": True, "computed_styles": True, "css_variables": True,
                         "interactions": False},
            "media": [{"role": "hero-visual", "reuse": "omit", "replacement": "generate"}],
            "coverage_gaps": ["hover states not captured"],
            "captures": [{"date": "2026-08-31", "archive": "captures/2026-08-31/raw/site.wacz"}],
        }))
        f = validate_bundle(str(good))
        if f.p0:
            print(f"FAIL good: {f.p0}")
            ok = False
        else:
            print(f"PASS good: P0=0 P1={len(f.p1)}")

        gap = base / "gap"
        write_fixture(gap, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {"interactions": False}, "coverage_gaps": [],
        }))
        f = validate_bundle(str(gap))
        if any("coverage_gaps" in m for m in f.p0):
            print("PASS undeclared-gap rejected")
        else:
            print(f"FAIL undeclared-gap not caught: {f.p0}")
            ok = False

        secret = base / "secret"
        write_fixture(secret, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {}, "apiKey": fixture_key,
        }))
        f = validate_bundle(str(secret))
        if any("credential-like" in m for m in f.p0):
            print("PASS secret rejected")
        else:
            print(f"FAIL secret not caught: {f.p0}")
            ok = False

        missing = base / "missing"
        write_fixture(missing, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {"screenshots": "captures/2026-08-31/screenshots/home-mobile.png"},
        }))
        f = validate_bundle(str(missing))
        if any("referenced file missing" in m for m in f.p0):
            print("PASS missing-file rejected")
        else:
            print(f"FAIL missing file not caught: {f.p0}")
            ok = False

        badscope = base / "badscope"
        write_fixture(badscope, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "everything",
            "evidence": {},
        }))
        f = validate_bundle(str(badscope))
        if any("scope" in m for m in f.p0):
            print("PASS bad-scope rejected")
        else:
            print(f"FAIL bad scope not caught: {f.p0}")
            ok = False

    print("web-reference manifest selftest: PASS" if ok else "web-reference manifest selftest: FAIL")
    return 0 if ok else 1


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args == ["--selftest"]:
        return selftest()
    total_p0 = 0
    for raw in args:
        findings = validate_bundle(raw)
        for m in findings.p0:
            print(f"P0  {raw}: {m}")
        for m in findings.p1:
            print(f"P1  {raw}: {m}")
        print(f"{raw}: P0={len(findings.p0)} P1={len(findings.p1)}")
        total_p0 += len(findings.p0)
    print("WEB REFERENCE MANIFEST: PASS" if total_p0 == 0 else "WEB REFERENCE MANIFEST: FAIL")
    return 0 if total_p0 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
