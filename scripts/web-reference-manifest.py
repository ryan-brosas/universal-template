#!/usr/bin/env python3
"""Validate exact structural and security contracts for web-reference bundles.

Coverage quality, trustworthiness, and ADOPT/ADAPT/OMIT decisions belong to
model review. This tool checks only parsing, types, enums, contained paths,
file existence, capture identity, and credential patterns.
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
EVIDENCE_KEYS = {"archive", "screenshots", "rendered_html", "source_html", "computed_styles", "css_variables", "interactions", "responsive"}
MEDIA_REUSE = {"omit", "adapt", "reuse"}
MEDIA_REPLACEMENT = {"generate", "css", "svg", "none", ""}
CAPTURE_ID_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2})(\d{2}))?$")
BINARY_SUFFIXES = {".7z", ".avif", ".bin", ".bmp", ".bz2", ".eot", ".gif", ".gz", ".ico", ".jpeg", ".jpg", ".mp3", ".mp4", ".mov", ".ogg", ".otf", ".pdf", ".png", ".tgz", ".ttf", ".wav", ".webm", ".webp", ".woff", ".woff2", ".wacz", ".xz", ".zip"}
SECRET_PATTERNS = (
    ("vendor credential", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"), True),
    ("credential assignment", re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|password|auth[_-]?token)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}"), False),
)
AUTHORED = {"manifest.json", "REFERENCE.md"}


def iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def contained(root: Path, relative: str) -> Path | None:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        return None
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return target


def file_ref(root: Path, relative: object, where: str, errors: list[str], allow_dir: bool = False) -> None:
    if not isinstance(relative, str):
        errors.append(f"{where}: path must be a string")
        return
    target = contained(root, relative)
    if target is None:
        errors.append(f"{where}: path must stay inside the bundle: {relative}")
    elif allow_dir and not target.is_dir():
        errors.append(f"{where}: referenced directory missing: {relative}")
    elif not allow_dir and not target.is_file():
        errors.append(f"{where}: referenced file missing: {relative}")


def capture_id(value: str) -> bool:
    match = CAPTURE_ID_RE.fullmatch(value)
    if not match:
        return False
    try:
        datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return match.group(4) is None or (int(match.group(4)) < 24 and int(match.group(5)) < 60)


def scan_credentials(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_bytes()[:20 * 1024 * 1024].decode("utf-8", errors="replace")
        except OSError:
            continue
        relative = str(path.relative_to(root))
        authored = relative in AUTHORED or relative.split("/", 1)[0] in {"design", "patterns"}
        for label, pattern, always_fail in SECRET_PATTERNS:
            if pattern.search(text) and (always_fail or authored):
                errors.append(f"{relative}: {label} must not be stored in a reference bundle")


def validate_bundle(raw_root: str) -> list[str]:
    errors: list[str] = []
    root = Path(raw_root).resolve()
    if not root.is_dir():
        return [f"not a directory: {raw_root}"]
    manifest_path = root / "manifest.json"
    reference_path = root / "REFERENCE.md"
    if not manifest_path.is_file():
        return ["manifest.json missing"]
    if not reference_path.is_file():
        errors.append("REFERENCE.md missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"manifest.json unreadable: {exc}"]
    if not isinstance(manifest, dict):
        return ["manifest.json must contain an object"]
    if manifest.get("type") != "web-reference":
        errors.append("manifest type must be 'web-reference'")
    source = manifest.get("source")
    parsed = urlparse(source) if isinstance(source, str) else None
    if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append("source must be an http(s) URL")
    captured_at = manifest.get("captured_at")
    if not isinstance(captured_at, str) or not iso8601(captured_at):
        errors.append("captured_at must be an ISO-8601 timestamp")
    if manifest.get("scope") not in SCOPES:
        errors.append(f"scope must be one of {sorted(SCOPES)}")
    coverage = manifest.get("coverage_gaps", [])
    if not isinstance(coverage, list) or not all(isinstance(item, str) for item in coverage):
        errors.append("coverage_gaps must be a list of strings")
    viewports = manifest.get("viewports", [])
    if not isinstance(viewports, list) or not all(isinstance(item, str) for item in viewports):
        errors.append("viewports must be a list of strings")
    evidence = manifest.get("evidence", {})
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    else:
        for key, value in evidence.items():
            if key not in EVIDENCE_KEYS:
                errors.append(f"evidence.{key}: unsupported key")
            if isinstance(value, str):
                file_ref(root, value, f"evidence.{key}", errors)
            elif not isinstance(value, bool):
                errors.append(f"evidence.{key}: value must be boolean or a bundle-relative path")
    pages = manifest.get("pages", [])
    if not isinstance(pages, list):
        errors.append("pages must be a list")
    else:
        for index, page in enumerate(pages):
            if not isinstance(page, dict) or not isinstance(page.get("route"), str) or not page["route"]:
                errors.append(f"pages[{index}]: route must be a non-empty string")
                continue
            if "path" in page:
                file_ref(root, page["path"], f"pages[{index}].path", errors, allow_dir=True)
            shots = page.get("screenshots", [])
            if not isinstance(shots, list):
                errors.append(f"pages[{index}].screenshots must be a list")
            else:
                for shot_index, shot in enumerate(shots):
                    file_ref(root, shot, f"pages[{index}].screenshots[{shot_index}]", errors)
    if manifest.get("scope") == "quick":
        screenshot_refs: list[object] = []
        if isinstance(evidence, dict):
            screenshot_refs.append(evidence.get("screenshots"))
        if isinstance(pages, list):
            for page in pages:
                if isinstance(page, dict) and isinstance(page.get("screenshots"), list):
                    screenshot_refs.extend(page["screenshots"])
        has_screenshot = any(
            isinstance(relative, str)
            and (target := contained(root, relative)) is not None
            and target.is_file()
            for relative in screenshot_refs
        )
        if not has_screenshot:
            errors.append(
                "quick capture must reference at least one existing screenshot file through "
                "evidence.screenshots or pages[].screenshots"
            )
    captures = manifest.get("captures", [])
    if not isinstance(captures, list):
        errors.append("captures must be a list")
    else:
        seen: set[str] = set()
        for index, item in enumerate(captures):
            value = item.get("id") if isinstance(item, dict) else None
            if not isinstance(value, str) or not capture_id(value):
                errors.append(f"captures[{index}].id must be a valid YYYY-MM-DD or YYYY-MM-DDTHHMM")
                continue
            if value in seen:
                errors.append(f"duplicate capture id: {value}")
            seen.add(value)
            if "archive" in item:
                file_ref(root, item["archive"], f"captures[{index}].archive", errors)
    media = manifest.get("media", [])
    if not isinstance(media, list):
        errors.append("media must be a list")
    else:
        for index, item in enumerate(media):
            if not isinstance(item, dict) or not isinstance(item.get("role"), str) or not item["role"]:
                errors.append(f"media[{index}].role must be a non-empty string")
                continue
            if item.get("reuse") not in MEDIA_REUSE:
                errors.append(f"media[{index}].reuse must be one of {sorted(MEDIA_REUSE)}")
            if item.get("replacement", "none") not in MEDIA_REPLACEMENT:
                errors.append(f"media[{index}].replacement must be one of {sorted(MEDIA_REPLACEMENT)}")
    scan_credentials(root, errors)
    return errors


def selftest() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "bundle"
        (root / "files").mkdir(parents=True)
        (root / "files" / "shot.png").write_bytes(b"png")
        (root / "REFERENCE.md").write_text("# Reference\n", encoding="utf-8")
        manifest = {
            "type": "web-reference", "source": "https://example.com",
            "captured_at": "2026-08-31T00:00:00Z", "scope": "quick",
            "evidence": {"screenshots": "files/shot.png"},
            "coverage_gaps": [], "captures": [{"id": "2026-08-31"}],
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if validate_bundle(str(root)):
            print("web-reference manifest selftest: FAIL valid fixture")
            return 1
        manifest["evidence"] = {"screenshots": True}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if not any("existing screenshot file" in error for error in validate_bundle(str(root))):
            print("web-reference manifest selftest: FAIL boolean screenshot evidence")
            return 1
        manifest["evidence"] = {"screenshots": False}
        manifest["coverage_gaps"] = ["screenshots: not captured"]
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if not any("existing screenshot file" in error for error in validate_bundle(str(root))):
            print("web-reference manifest selftest: FAIL screenshot coverage gap")
            return 1
        manifest["pages"] = [{"route": "/", "screenshots": ["files/shot.png"]}]
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if validate_bundle(str(root)):
            print("web-reference manifest selftest: FAIL page screenshot fixture")
            return 1
        manifest.pop("pages")
        manifest["coverage_gaps"] = []
        manifest["evidence"] = {"screenshots": "../escape.png"}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if not any("inside the bundle" in error for error in validate_bundle(str(root))):
            print("web-reference manifest selftest: FAIL escaping path")
            return 1
        manifest["evidence"] = {}
        manifest["api_key"] = "sk-" + "x" * 24
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if not any("credential" in error for error in validate_bundle(str(root))):
            print("web-reference manifest selftest: FAIL credential")
            return 1
    print("web-reference manifest selftest: PASS")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args == ["--selftest"]:
        return selftest()
    if not args:
        print(__doc__)
        return 2
    count = 0
    for raw_root in args:
        errors = validate_bundle(raw_root)
        for error in errors:
            print(f"FAIL  {raw_root}: {error}")
        print(f"{raw_root}: {len(errors)} fail")
        count += len(errors)
    print("WEB REFERENCE MANIFEST: PASS" if count == 0 else "WEB REFERENCE MANIFEST: FAIL")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
