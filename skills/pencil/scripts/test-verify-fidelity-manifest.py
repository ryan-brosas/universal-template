#!/usr/bin/env python3
"""Exercise evidence boundaries through the public manifest CLI."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ManifestEvidenceTests(unittest.TestCase):
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

    def check_manifest(self, accepted, diagnostic="font", raw=None, env=None):
        self.path.write_bytes(raw if raw is not None else json.dumps(self.data).encode("utf-8"))
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("verify-fidelity-manifest.py")),
             str(self.path)], capture_output=True, text=True, check=False, env=env,
        )
        self.assertEqual(result.returncode, 0 if accepted else 1, result.stdout + result.stderr)
        if not accepted:
            self.assertIn(diagnostic, result.stderr.lower())
            self.assertNotIn("Traceback", result.stderr)

    def test_utf8_ids_under_ascii_locale(self):
        self.data['target']['fileId'] = 'café-東京'
        raw = json.dumps(self.data, ensure_ascii=False).encode('utf-8')
        env = dict(os.environ, LC_ALL='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0')
        self.check_manifest(True, raw=raw, env=env)

    def test_invalid_utf8(self):
        self.check_manifest(False, "cannot read manifest", raw=b"\xff\xfe")

    def test_non_object_roots(self):
        for value in (None, [], "manifest", True, 0):
            with self.subTest(value=value):
                self.data = value
                self.check_manifest(False, "manifest")

    def test_non_object_sections(self):
        for section in ("target", "artifacts", "structure", "assets", "visual", "theme"):
            original = self.data[section]
            for value in (None, [], "section", True, 0):
                with self.subTest(section=section, value=value):
                    self.data[section] = value
                    self.check_manifest(False, section)
            self.data[section] = original

    def test_numeric_evidence_requires_integer_zero(self):
        for section, keys in (("structure", ("nameMismatches", "boundsMismatches", "countMismatches")),
                              ("assets", ("flattenedScreenshotRefs",))):
            for key in keys:
                for value in (False, True, "0", None, -1, 1, 0.0, [], {}):
                    with self.subTest(section=section, key=key, value=value):
                        self.data[section][key] = value
                        self.check_manifest(False, key.lower())
                self.data[section][key] = 0

    def test_malformed_leaf_values(self):
        for section, key in (("target", "fileId"), ("target", "pageId"), ("target", "nodeId"),
                             *(("artifacts", key) for key in self.data["artifacts"])):
            original = self.data[section][key]
            for value in (True, 1, [], {}, None, "", "  ", "bad\u0000path"):
                with self.subTest(section=section, key=key, value=value):
                    self.data[section][key] = value
                    self.check_manifest(False, key.lower())
            self.data[section][key] = original
        for status in ([], {}, None, True):
            with self.subTest(status=status):
                self.data["status"] = status
                self.check_manifest(False, "status")

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
