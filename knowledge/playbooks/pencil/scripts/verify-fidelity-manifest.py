#!/usr/bin/env python3
"""Fail closed when a Paper/Figma fidelity manifest lacks completion evidence."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def fail(messages: list[str]) -> int:
    for message in messages:
        print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        return fail(["usage: verify-fidelity-manifest.py <manifest.json>"])

    manifest_path = Path(sys.argv[1])
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return fail([f"cannot read manifest: {exc}"])

    if not isinstance(data, dict):
        return fail(["manifest must be an object"])
    errors = [f"{section} must be an object" for section in (
        "target", "artifacts", "structure", "assets", "visual", "theme"
    ) if not isinstance(data.get(section), dict)]
    if errors:
        return fail(errors)

    status = data.get("status")
    if status not in ("pixel-perfect", "approved-fallback"):
        errors.append("status must be pixel-perfect or approved-fallback")

    target = data.get("target", {})
    for key in ("fileId", "pageId", "nodeId"):
        value = target.get(key)
        if not isinstance(value, str) or not value.strip() or "\0" in value:
            errors.append(f"target.{key} must be a nonempty string without NULs")

    artifacts = data.get("artifacts", {})
    for key in ("sourceScreenshot", "paperScreenshot", "diffImage", "structuralAudit"):
        value = artifacts.get(key)
        if not isinstance(value, str) or not value.strip() or "\0" in value:
            errors.append(f"artifacts.{key} must be a nonempty path string without NULs")
            continue
        try:
            if not os.path.isfile(value) or os.path.getsize(value) == 0:
                errors.append(f"artifacts.{key} does not exist or is empty")
        except (OSError, ValueError):
            errors.append(f"artifacts.{key} cannot be inspected")

    structure = data.get("structure", {})
    for key in ("nameMismatches", "boundsMismatches", "countMismatches"):
        if type(structure.get(key)) is not int or structure[key] != 0:
            errors.append(f"structure.{key} must be integer 0")

    flattened = data["assets"].get("flattenedScreenshotRefs")
    if type(flattened) is not int or flattened != 0:
        errors.append("assets.flattenedScreenshotRefs must be integer 0")
    if data.get("visual", {}).get("status") != "passed":
        errors.append("visual.status must be passed")
    if data.get("theme", {}).get("status") != "passed":
        errors.append("theme.status must be passed")

    fonts = data.get("fonts")
    if not isinstance(fonts, dict):
        errors.append("fonts must be an object with explicit availability evidence")
        fonts = {}
    unavailable = fonts.get("unavailable")
    if not isinstance(unavailable, list) or any(
        not isinstance(name, str) or not name.strip() for name in unavailable
    ):
        errors.append("fonts.unavailable must be a list of nonempty font names")
        unavailable = []
    if not isinstance(fonts.get("fallbackApproved"), bool):
        errors.append("fonts.fallbackApproved must be a boolean")
    fallback_approved = fonts.get("fallbackApproved") is True
    if status == "pixel-perfect" and unavailable:
        errors.append("pixel-perfect cannot have unavailable source fonts")
    if status == "approved-fallback" and (not unavailable or not fallback_approved):
        errors.append("approved-fallback requires unavailable fonts and fallbackApproved=true")

    if errors:
        return fail(errors)
    print(f"PASS: {status} evidence is complete for {target['nodeId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
