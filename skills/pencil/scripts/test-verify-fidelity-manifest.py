#!/usr/bin/env python3
"""Exercise font-evidence boundaries through the public manifest CLI."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class FontEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        artifact = root / "evidence"
        artifact.write_text("fixture: completeness only, not visual fidelity")
        self.path = root / "manifest.json"
        self.data = {
            "status": "pixel-perfect",
            "target": dict(fileId="file", pageId="page", nodeId="node"),
            "artifacts": {key: str(artifact) for key in (
                "sourceScreenshot", "paperScreenshot", "diffImage", "structuralAudit"
            )},
            "structure": dict(nameMismatches=0, boundsMismatches=0, countMismatches=0),
            "assets": {"flattenedScreenshotRefs": 0},
            "visual": {"status": "passed"},
            "theme": {"status": "passed"},
            "fonts": {"unavailable": [], "fallbackApproved": False},
        }

    def check_manifest(self, accepted):
        self.path.write_text(json.dumps(self.data))
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("verify-fidelity-manifest.py")),
             str(self.path)], capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0 if accepted else 1, result.stdout + result.stderr)
        if not accepted:
            self.assertIn("font", result.stderr.lower())
            self.assertNotIn("Traceback", result.stderr)

    def test_explicit_available_fonts(self):
        self.check_manifest(True)

    def test_missing_font_section(self):
        del self.data["fonts"]
        self.check_manifest(False)

    def test_incomplete_or_malformed_font_evidence(self):
        for fonts in (None, [], "available", {}, {"fallbackApproved": False},
                      {"unavailable": []},
                      {"unavailable": None, "fallbackApproved": False},
                      {"unavailable": "", "fallbackApproved": False},
                      {"unavailable": [7], "fallbackApproved": False},
                      {"unavailable": ["  "], "fallbackApproved": False},
                      {"unavailable": [], "fallbackApproved": "false"}):
            with self.subTest(fonts=fonts):
                self.data["fonts"] = fonts
                self.check_manifest(False)

    def test_missing_font_cannot_be_pixel_perfect_even_with_approval(self):
        self.data["fonts"] = {"unavailable": ["Source Sans"], "fallbackApproved": True}
        self.check_manifest(False)

    def test_fallback_requires_explicit_approval(self):
        self.data["status"] = "approved-fallback"
        for approval in (False, "true", 1):
            with self.subTest(approval=approval):
                self.data["fonts"] = {"unavailable": ["Source Sans"], "fallbackApproved": approval}
                self.check_manifest(False)
        self.data["fonts"]["fallbackApproved"] = True
        self.check_manifest(True)

    def test_fallback_requires_named_missing_font(self):
        self.data["status"] = "approved-fallback"
        self.data["fonts"] = {"unavailable": [], "fallbackApproved": True}
        self.check_manifest(False)


if __name__ == "__main__":
    unittest.main()
