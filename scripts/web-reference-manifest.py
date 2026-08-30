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
MAX_SCAN_BYTES = 20 * 1024 * 1024
ARCHIVE_WARN_BYTES = 25 * 1024 * 1024
BINARY_SUFFIXES = {
    ".7z", ".avif", ".bin", ".bmp", ".bz2", ".dat", ".eot", ".gif", ".gz",
    ".ico", ".jpeg", ".jpg", ".mp3", ".mp4", ".mov", ".ogg", ".otf", ".pdf",
    ".png", ".tgz", ".ttf", ".wav", ".webm", ".webp", ".woff", ".woff2",
    ".wacz", ".xz", ".zip",
}
CAPTURE_ID_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2})(\d{2}))?$")
# Capture validation owns structural truth, not implementation decisions.
# quick = one visual evidence artifact (screenshot) plus a truthful manifest;
# rendered HTML, styles, and fonts stay optional and can be declared as gaps.
EXPECTED_EVIDENCE = {
    "quick": {"screenshots"},
    "page": {"screenshots", "rendered_html"},
    "site": {"screenshots", "rendered_html"},
    "deep": {"screenshots", "rendered_html", "computed_styles", "css_variables"},
}

# Secret hygiene distinguishes authored metadata from raw captured evidence.
# Authored files are written by the agent: credential-like material there is a
# P0. Raw captures (rendered HTML, extracted CSS/JSON) can legitimately contain
# public documentation examples — those get a review warning, never a silent
# store. Private session material (cookies, auth headers, localStorage) must
# never be captured in the first place; that rule lives in the skill.
AUTHORED_SECRET_FILES = {"manifest.json", "REFERENCE.md"}
AUTHORED_SECRET_DIRS = {"design", "patterns"}


def is_authored_file(rel: str) -> bool:
    parts = rel.split("/")
    if len(parts) == 1 and parts[0] in AUTHORED_SECRET_FILES:
        return True
    return len(parts) >= 2 and parts[0] in AUTHORED_SECRET_DIRS

# (label, pattern, class). "key" = vendor-format credential: real wherever it
# appears, including raw captures. "sample" = bearer/labeled form that public
# documentation legitimately shows: a hard failure in authored metadata, a
# review warning in raw captured evidence. Private session material (cookies,
# auth headers from the user's session, localStorage, session tokens) must
# never be captured in the first place; that rule lives in the skill.
SECRET_PATTERNS = [
    ("openai-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "key"),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "key"),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "key"),
    ("bearer header", re.compile(r"(?i)authorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._-]+"), "sample"),
    ("labeled secret", re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|password|auth[_-]?token)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}"), "sample"),
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


def check_capture_id(value: str, findings: Findings, where: str) -> None:
    m = CAPTURE_ID_RE.match(value)
    if not m:
        findings.fail(f"{where}: capture id must be YYYY-MM-DD or YYYY-MM-DDTHHMM: {value}")
        return
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        datetime(year, month, day)
    except ValueError:
        findings.fail(f"{where}: capture id is not a real calendar date: {value}")
        return
    if m.group(4) is not None and (int(m.group(4)) > 23 or int(m.group(5)) > 59):
        findings.fail(f"{where}: capture id time is not a valid HHMM: {value}")


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


def walk_text_files(root: Path) -> list[tuple[Path, bool]]:
    """Every bundle file that is not a known binary, flagged when oversized."""
    out: list[tuple[Path, bool]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        if p.suffix.lower() in BINARY_SUFFIXES:
            continue
        out.append((p, p.stat().st_size > MAX_SCAN_BYTES))
    return out


def scan_secrets(root: Path, findings: Findings) -> None:
    for p, oversized in walk_text_files(root):
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:1024]:
            continue
        if oversized:
            findings.warn(
                f"{p.relative_to(root)}: larger than {MAX_SCAN_BYTES // (1024 * 1024)}MB; "
                f"credential scan covered the first {MAX_SCAN_BYTES // (1024 * 1024)}MB only"
            )
        text = data[:MAX_SCAN_BYTES].decode("utf-8", errors="replace")
        rel = str(p.relative_to(root))
        authored = is_authored_file(rel)
        for label, pattern, kind in SECRET_PATTERNS:
            if not pattern.search(text):
                continue
            if authored:
                findings.fail(
                    f"{rel}: credential-like material ({label}) in authored metadata "
                    f"must never be stored in a reference bundle")
            elif kind == "key":
                # A vendor-format key in captured content is a real credential
                # leak far more often than a docs example: quarantine the file.
                findings.fail(
                    f"{rel}: vendor-format credential ({label}) in captured evidence "
                    f"must be removed or re-captured without it before the bundle is "
                    f"committed or shared")
            else:
                findings.warn(
                    f"{rel}: credential-like sample ({label}) in raw captured evidence — "
                    f"likely public documentation; review and quarantine before the bundle "
                    f"is reused. Never store private session material (cookies, auth "
                    f"headers, localStorage, session tokens).")


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
    if not isinstance(manifest, dict):
        findings.fail("manifest.json must contain an object")
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

    expected_evidence = EXPECTED_EVIDENCE.get(scope, set())

    def gap_declares(key: str) -> bool:
        variants = (key, key.replace("_", " "))
        gaps = coverage if isinstance(coverage, list) else []
        return any(
            variant in gap.lower()
            for gap in gaps
            if isinstance(gap, str)
            for variant in variants
        )

    pages = manifest.get("pages", [])
    if not isinstance(pages, list):
        findings.fail("pages must be a list")
        pages = []
    routes: set[str] = set()
    pages_have_shots = False
    for i, page in enumerate(pages):
        if not isinstance(page, dict) or not isinstance(page.get("route"), str) or not page["route"]:
            findings.fail(f"pages[{i}] needs a route string")
            continue
        shots = page.get("screenshots")
        if isinstance(shots, list) and shots:
            pages_have_shots = True

    evidence = manifest.get("evidence", {})
    if not isinstance(evidence, dict):
        findings.fail("evidence must be an object")
        evidence = {}
    for key, value in evidence.items():
        if key not in EVIDENCE_KEYS:
            findings.warn(f"evidence.{key} is not a known evidence key")
        if isinstance(value, bool):
            if value is False and not gap_declares(key):
                findings.fail(f"evidence.{key} is false but coverage_gaps does not name it: a partial capture must be declared")
        elif isinstance(value, str):
            check_file_ref(root, value, findings, f"evidence.{key}")
        else:
            findings.fail(f"evidence.{key} must be a boolean or a bundle-relative path")
    for key in sorted(expected_evidence):
        if key in evidence:
            continue
        if key == "screenshots" and pages_have_shots:
            continue  # page-level screenshots satisfy the quick contract
        if not gap_declares(key):
            findings.fail(f"evidence.{key} is expected for scope '{scope}' but absent and coverage_gaps does not declare it")

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

    # Quick contract: the one mandatory artifact is a real screenshot file.
    # A boolean true or a coverage_gaps entry must not satisfy it — without a
    # visual artifact there is no quick capture at all.
    if scope == "quick":
        shot = evidence.get("screenshots")
        shot_path = resolve_under(root, shot) if isinstance(shot, str) else None
        shot_ok = shot_path is not None and shot_path.is_file()
        page_shots = any(
            isinstance(page.get("screenshots"), list) and page["screenshots"]
            for page in pages if isinstance(page, dict))
        if not shot_ok and not page_shots:
            findings.fail(
                "quick capture needs at least one real screenshot file "
                "(evidence.screenshots as a bundle-relative path, or a non-empty "
                "pages[].screenshots); a boolean or a coverage gap does not "
                "satisfy the quick contract")

    viewports = manifest.get("viewports", [])
    if not isinstance(viewports, list) or not all(isinstance(v, str) for v in viewports):
        findings.fail("viewports must be a list of strings")
    elif scope in {"site", "deep"} and not viewports:
        findings.warn("site/deep capture declares no viewports")

    captures = manifest.get("captures", [])
    if not isinstance(captures, list):
        findings.fail("captures must be a list")
        captures = []
    capture_ids: set[str] = set()
    for i, cap in enumerate(captures):
        if not isinstance(cap, dict) or not isinstance(cap.get("id"), str):
            findings.fail(f"captures[{i}] needs an id string (YYYY-MM-DD or YYYY-MM-DDTHHMM)")
            continue
        if cap["id"] in capture_ids:
            findings.fail(f"duplicate capture id: {cap['id']}")
        capture_ids.add(cap["id"])
        check_capture_id(cap["id"], findings, f"captures[{i}].id")
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
        missing_tokens = [token for token in ("ADOPT", "ADAPT", "OMIT")
                          if not re.search(rf"^##\s+{token}\s*$", text, re.MULTILINE)]
        if missing_tokens:
            # A capture may exist before the project decides how to use it.
            # ADOPT / ADAPT / OMIT is the implementation decision recorded by
            # reference-driven-development, not a capture requirement.
            findings.warn(
                "REFERENCE.md has no " + "/".join(missing_tokens) +
                " decision section yet — capture is valid; record ADOPT / ADAPT / "
                "OMIT when the reference enters implementation "
                "(reference-driven-development)")

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
            "coverage_gaps": ["interactions: hover states not captured"],
            "captures": [{"id": "2026-08-31", "archive": "captures/2026-08-31/raw/site.wacz"},
                         {"id": "2026-08-31T1435"}],
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

        emptyevidence = base / "emptyevidence"
        write_fixture(emptyevidence, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "site",
            "evidence": {}, "coverage_gaps": [],
        }))
        f = validate_bundle(str(emptyevidence))
        if any("expected for scope" in m for m in f.p0):
            print("PASS empty-evidence rejected")
        else:
            print(f"FAIL empty evidence not caught: {f.p0}")
            ok = False

        badtype = base / "badtype"
        write_fixture(badtype, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {"screenshots": 3}, "coverage_gaps": [],
        }))
        f = validate_bundle(str(badtype))
        if any("boolean or a bundle-relative path" in m for m in f.p0):
            print("PASS bad-evidence-type rejected")
        else:
            print(f"FAIL bad evidence type not caught: {f.p0}")
            ok = False

        notobject = base / "notobject"
        write_fixture(notobject, "[]")
        f = validate_bundle(str(notobject))
        if any("must contain an object" in m for m in f.p0):
            print("PASS non-object manifest rejected")
        else:
            print(f"FAIL non-object manifest not caught: {f.p0}")
            ok = False

        dupid = base / "dupid"
        write_fixture(dupid, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {}, "coverage_gaps": [],
            "captures": [{"id": "2026-08-31"}, {"id": "2026-08-31"}],
        }))
        f = validate_bundle(str(dupid))
        if any("duplicate capture id" in m for m in f.p0):
            print("PASS duplicate capture id rejected")
        else:
            print(f"FAIL duplicate capture id not caught: {f.p0}")
            ok = False

        badid = base / "badid"
        write_fixture(badid, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {}, "coverage_gaps": [],
            "captures": [{"id": "2026-13-45"}],
        }))
        f = validate_bundle(str(badid))
        if any("not a real calendar date" in m for m in f.p0):
            print("PASS invalid capture id rejected")
        else:
            print(f"FAIL invalid capture id not caught: {f.p0}")
            ok = False

        prose = base / "prose"
        (prose / "captures" / "2026-08-31" / "screenshots").mkdir(parents=True)
        (prose / "captures" / "2026-08-31" / "screenshots" / "hero.png").write_bytes(b"png")
        (prose / "REFERENCE.md").write_text("# Website Reference\n", encoding="utf-8")
        (prose / "manifest.json").write_text(json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "evidence": {"screenshots": "captures/2026-08-31/screenshots/hero.png"},
            "coverage_gaps": [],
        }), encoding="utf-8")
        (prose / "REFERENCE.md").write_text(
            "We do not ADOPT, ADAPT, or OMIT anything here.\n", encoding="utf-8")
        f = validate_bundle(str(prose))
        if not f.p0 and any("decision section" in m for m in f.p1):
            print("PASS capture without decision sections warns, does not fail")
        else:
            print(f"FAIL expected P1 decision-section warning, got P0={f.p0} P1={f.p1}")
            ok = False

        # Golden test: quick capture = source URL, timestamp, one visual
        # artifact, truthful manifest. No rendered HTML required.
        quick = base / "quick"
        (quick / "captures" / "2026-08-31" / "screenshots").mkdir(parents=True)
        (quick / "captures" / "2026-08-31" / "screenshots" / "hero-desktop.png").write_bytes(b"png")
        (quick / "REFERENCE.md").write_text(
            "# Website Reference\n\nA hero region worth revisiting.\n", encoding="utf-8")
        (quick / "manifest.json").write_text(json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "evidence": {"screenshots": "captures/2026-08-31/screenshots/hero-desktop.png"},
            "coverage_gaps": ["rendered_html and styles not collected (quick mode)"],
        }), encoding="utf-8")
        f = validate_bundle(str(quick))
        if not f.p0:
            print(f"PASS quick capture with one screenshot only: P0=0 P1={len(f.p1)}")
        else:
            print(f"FAIL quick capture rejected: {f.p0}")
            ok = False

        # Quick contract: a boolean true is not a screenshot.
        boolshot = base / "boolshot"
        boolshot.mkdir()
        (boolshot / "REFERENCE.md").write_text("# Website Reference\n", encoding="utf-8")
        (boolshot / "manifest.json").write_text(json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "evidence": {"screenshots": True}, "coverage_gaps": [],
        }), encoding="utf-8")
        f = validate_bundle(str(boolshot))
        if any("quick capture needs" in m for m in f.p0):
            print("PASS quick boolean screenshot rejected")
        else:
            print(f"FAIL quick boolean screenshot accepted: {f.p0}")
            ok = False

        # Quick contract: a declared gap does not replace the visual artifact.
        gapshot = base / "gapshot"
        gapshot.mkdir()
        (gapshot / "REFERENCE.md").write_text("# Website Reference\n", encoding="utf-8")
        (gapshot / "manifest.json").write_text(json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "evidence": {}, "coverage_gaps": ["screenshots not captured"],
        }), encoding="utf-8")
        f = validate_bundle(str(gapshot))
        if any("quick capture needs" in m for m in f.p0):
            print("PASS quick gap-declared screenshot rejected")
        else:
            print(f"FAIL quick gap-declared screenshot accepted: {f.p0}")
            ok = False

        # A page-level screenshot also satisfies the quick contract.
        pageshot = base / "pageshot"
        (pageshot / "captures" / "2026-08-31" / "screenshots").mkdir(parents=True)
        (pageshot / "captures" / "2026-08-31" / "screenshots" / "hero.png").write_bytes(b"png")
        (pageshot / "REFERENCE.md").write_text("# Website Reference\n", encoding="utf-8")
        (pageshot / "manifest.json").write_text(json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "pages": [{"route": "/", "screenshots": ["captures/2026-08-31/screenshots/hero.png"]}],
            "evidence": {}, "coverage_gaps": [],
        }), encoding="utf-8")
        f = validate_bundle(str(pageshot))
        if not f.p0:
            print("PASS quick page-level screenshot accepted")
        else:
            print(f"FAIL quick page-level screenshot rejected: {f.p0}")
            ok = False

        # Golden test: public doc example in raw capture warns; authored
        # metadata with the same material stays a hard failure.
        rawsample = base / "rawsample"
        write_fixture(rawsample, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {"rendered_html": "captures/2026-08-31/pages/home/rendered.html"},
            "coverage_gaps": ["screenshots and remaining evidence omitted"],
        }))
        (rawsample / "captures" / "2026-08-31" / "pages" / "home" / "rendered.html").write_text(
            "Authorization: Bearer " + "b" * 24 + "\n", encoding="utf-8")
        f = validate_bundle(str(rawsample))
        if not f.p0 and any("raw captured evidence" in m for m in f.p1):
            print("PASS secret sample in raw capture warns for review")
        else:
            print(f"FAIL expected raw-capture warning, got P0={f.p0} P1={f.p1}")
            ok = False
        (rawsample / "REFERENCE.md").write_text(
            GOOD_REFERENCE + "\nAuthorization: Bearer " + "b" * 24 + "\n", encoding="utf-8")
        f = validate_bundle(str(rawsample))
        if any("authored metadata" in m for m in f.p0):
            print("PASS secret in authored metadata stays a hard failure")
        else:
            print(f"FAIL expected authored-metadata P0, got P0={f.p0}")
            ok = False

        # A vendor-format key in a raw capture is a real leak: hard failure
        # even outside authored metadata.
        keysample = base / "keysample"
        write_fixture(keysample, json.dumps({
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "page",
            "evidence": {"rendered_html": "captures/2026-08-31/pages/home/rendered.html"},
            "coverage_gaps": ["screenshots and remaining evidence omitted"],
        }))
        (keysample / "captures" / "2026-08-31" / "pages" / "home" / "rendered.html").write_text(
            "api_key = " + "sk-" + "k" * 24 + "\n", encoding="utf-8")
        f = validate_bundle(str(keysample))
        if any("vendor-format credential" in m for m in f.p0):
            print("PASS vendor-format key in raw capture fails")
        else:
            print(f"FAIL vendor-format key in raw capture passed: P0={f.p0}")
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
