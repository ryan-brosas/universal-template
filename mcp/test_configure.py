"""Ownership and file-safety regressions; run through configure.py --selftest."""
from __future__ import annotations

import importlib.util
import json
import os
import errno
import struct
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name("configure.py")
spec = importlib.util.spec_from_file_location("mcp_configure", SCRIPT)
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mcp-ownership-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "settings.json"
        self.original = {"theme": "dark", "mcpServers": {"personal": {"command": "keep"}}}
        self.target.write_text(json.dumps(self.original) + "\n", encoding="utf-8")

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(self.target), *args],
            capture_output=True, text=True,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def current(self):
        return json.loads(self.target.read_text(encoding="utf-8"))

    def test_minimal_removes_managed_preserves_unmanaged(self):
        self.cli("--profile", "docs", "--apply")
        self.cli("--profile", "minimal", "--apply")
        self.assertEqual(self.current(), self.original)

    def test_unmanaged_same_name_conflicts_even_if_identical(self):
        self.original["mcpServers"]["context7"] = configure.translate(
            configure.selection("docs", None)[1]["context7"], "generic"
        )
        self.target.write_text(json.dumps(self.original), encoding="utf-8")
        before = self.target.read_bytes()
        self.cli("--profile", "docs", "--apply", ok=False)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [self.target])

    def test_profile_switch_and_single_server_addition(self):
        self.cli("--profile", "docs", "--apply")
        self.cli("--server", "exa", "--apply")
        self.assertEqual(set(self.current()["mcpServers"]), {"personal", "context7", "exa"})
        self.cli("--profile", "code-graph", "--apply")
        self.assertEqual(set(self.current()["mcpServers"]), {"personal", "codebase-memory"})
        self.cli("--profile", "code-graph", "--deactivate", "--apply")
        self.assertEqual(self.current(), self.original)

    def test_preview_is_read_only_and_does_not_expose_values(self):
        self.original["mcpServers"]["personal"]["credential"] = "fixture-private-value"
        self.target.write_text(json.dumps(self.original), encoding="utf-8")
        before = self.snapshot()
        result = self.cli("--profile", "docs")
        self.assertNotIn("fixture-private-value", result.stdout + result.stderr)
        self.assertIn('"add": [', result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.target = self.root / "missing" / "settings.json"
        self.cli("--profile", "docs")
        self.assertFalse(self.target.parent.exists())

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def test_explicit_replacement_and_first_backup(self):
        self.original["mcpServers"]["context7"] = {"command": "personal-command"}
        raw = json.dumps(self.original).encode()
        self.target.write_bytes(raw)
        self.cli("--profile", "docs", "--replace-unmanaged")
        self.assertEqual(self.snapshot(), {self.target.name: raw})
        self.cli("--profile", "docs", "--replace-unmanaged", "--apply")
        backup = configure.backup_path(self.target)
        self.assertEqual(backup.read_bytes(), raw)
        self.cli("--profile", "minimal", "--apply")
        self.assertNotIn("context7", self.current()["mcpServers"])
        self.assertEqual(backup.read_bytes(), raw)
        if os.name == "posix":
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(configure.sidecar(self.target).stat().st_mode & 0o777, 0o600)

    def test_edited_managed_entry_is_preserved_and_ownership_relinquished(self):
        self.cli("--profile", "docs", "--apply")
        edited = self.current()
        edited["mcpServers"]["context7"]["command"] = "user-edited"
        self.target.write_text(json.dumps(edited), encoding="utf-8")
        before = self.snapshot()
        self.cli("--profile", "docs", "--apply", ok=False)
        self.assertEqual(self.snapshot(), before)
        result = self.cli("--profile", "minimal", "--apply")
        self.assertIn('"preserve_modified": [', result.stdout)
        self.assertEqual(self.current(), edited)
        self.assertEqual(configure.load_json(configure.sidecar(self.target))["managed"], {})

    def test_deactivation_never_removes_unmanaged_entries(self):
        self.original["mcpServers"]["context7"] = {"command": "keep-user"}
        self.target.write_text(json.dumps(self.original), encoding="utf-8")
        self.cli("--server", "context7", "--deactivate", "--apply")
        self.assertEqual(self.current(), self.original)
        self.cli("--profile", "docs", "--deactivate", "--replace-unmanaged", ok=False)

    def test_empty_minimal_is_noop_and_creation_is_private(self):
        self.target.unlink()
        self.cli("--profile", "minimal", "--apply")
        self.assertEqual(list(self.root.iterdir()), [])
        self.cli("--profile", "docs", "--apply")
        self.assertFalse(configure.backup_path(self.target).exists())
        if os.name == "posix":
            self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)

    def test_empty_apply_does_not_create_missing_parent(self):
        self.target = self.root / "missing" / "nested" / "settings.json"
        self.cli("--profile", "minimal", "--apply")
        self.assertFalse((self.root / "missing").exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux access metadata")
    def test_existing_acl_is_preserved(self):
        acl = struct.pack("<I", 2) + b"".join(
            struct.pack("<HHI", tag, permissions, identifier)
            for tag, permissions, identifier in [
                (1, 6, 0xffffffff), (2, 4, 65534), (4, 4, 0xffffffff),
                (16, 4, 0xffffffff), (32, 0, 0xffffffff),
            ]
        )
        try:
            os.setxattr(self.target, "system.posix_acl_access", acl)
        except OSError as exc:
            if exc.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
                self.skipTest("filesystem does not support POSIX ACLs")
            raise
        self.cli("--profile", "docs", "--apply")
        self.assertEqual(os.getxattr(self.target, "system.posix_acl_access"), acl)
        self.cli("--profile", "minimal", "--apply")
        self.assertEqual(os.getxattr(self.target, "system.posix_acl_access"), acl)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux access metadata")
    def test_existing_custom_group_is_preserved(self):
        groups = [gid for gid in os.getgroups() if gid != os.getegid()]
        if not groups:
            self.skipTest("no supplementary group available")
        os.chown(self.target, -1, groups[0])
        self.cli("--profile", "docs", "--apply")
        self.assertEqual(self.target.stat().st_gid, groups[0])

    def test_unsupported_access_metadata_fails_before_target_or_journal_write(self):
        before = self.snapshot()
        with mock.patch.object(configure.sys, "platform", "unsupported-platform"):
            with self.assertRaisesRegex(ValueError, "access-metadata support"):
                self.run_direct()
        self.assertEqual(self.snapshot(), before)

    def test_metadata_copy_failure_preserves_target(self):
        before = self.target.read_bytes()
        with mock.patch.object(configure, "set_access_metadata", side_effect=PermissionError("fixture denial")):
            with self.assertRaises(PermissionError):
                self.run_direct()
        self.assertEqual(self.target.read_bytes(), before)
        self.assertIn("pending", configure.load_json(configure.sidecar(self.target)))
        self.cli("--profile", "docs", "--apply")
        self.assertNotIn("pending", configure.load_json(configure.sidecar(self.target)))

    def test_noop_does_not_rewrite_files(self):
        self.cli("--profile", "docs", "--apply")
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        self.cli("--profile", "docs", "--apply")
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}, before)

    def test_malformed_target_and_state_are_rejected(self):
        for content in ('[]', '{', '{"mcpServers":[]}'):
            with self.subTest(content=content):
                self.target.write_text(content, encoding="utf-8")
                before = self.snapshot()
                self.cli("--profile", "docs", "--apply", ok=False)
                self.assertEqual(self.snapshot(), before)
        self.target.write_text(json.dumps(self.original), encoding="utf-8")
        state_path = configure.sidecar(self.target)
        invalid_states = [
            {}, {"version": True, "target": str(self.target), "managed": {}},
            {"version": 1, "target": "other", "managed": {}},
            {"version": 1, "target": str(self.target), "managed": {"personal": "bad"}},
            {"version": 1, "target": str(self.target), "managed": {}, "pending": {}},
        ]
        for state in invalid_states:
            with self.subTest(state=state):
                state_path.write_text(json.dumps(state), encoding="utf-8")
                before = self.snapshot()
                self.cli("--profile", "docs", "--apply", ok=False)
                self.assertEqual(self.snapshot(), before)

    @unittest.skipUnless(os.name == "posix", "symlink fixture requires POSIX")
    def test_symlink_targets_sidecars_and_backups_are_rejected(self):
        other = self.root / "other.json"
        other.write_text('{}', encoding="utf-8")
        for path in (self.target, configure.sidecar(self.target), configure.backup_path(self.target)):
            with self.subTest(path=path):
                if path == self.target:
                    path.unlink()
                path.symlink_to(other)
                self.cli("--profile", "docs", "--apply", ok=False)
                self.assertEqual(other.read_text(), '{}')
                path.unlink()
                if path == self.target:
                    self.target.write_text(json.dumps(self.original), encoding="utf-8")

    def test_existing_lock_blocks_writes(self):
        lock = configure.lock_path(self.target)
        lock.write_text("fixture lock", encoding="utf-8")
        before = self.snapshot()
        self.cli("--profile", "docs", "--apply", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_atomic_replace_failure_preserves_original_and_cleans_temp(self):
        before = self.snapshot()
        def fail(_source, _target):
            raise OSError("injected replacement failure")
        with self.assertRaises(OSError):
            configure.atomic_write(self.target, b'{}\n', replace=fail)
        self.assertEqual(self.snapshot(), before)

    def test_atomic_readback_detects_corruption(self):
        def corrupt(source, target):
            source.write_bytes(b'{"unexpected":true}\n')
            os.replace(source, target)
        with self.assertRaisesRegex(OSError, "read-back"):
            configure.atomic_write(self.target, b'{}\n', replace=corrupt)
        self.assertFalse(list(self.root.glob('.settings.json.*')))

    def run_direct(self, profile="docs"):
        names, registry = configure.selection(profile, None)
        return configure.configure_target(self.target, names, registry, profile=True, apply=True)

    def test_recovery_when_target_write_fails(self):
        real = configure.atomic_write
        original = self.target.read_bytes()
        def fail_target(path, raw, **kwargs):
            if path == self.target:
                raise OSError("injected target failure")
            return real(path, raw, **kwargs)
        with mock.patch.object(configure, "atomic_write", side_effect=fail_target):
            with self.assertRaises(OSError):
                self.run_direct()
        self.assertEqual(self.target.read_bytes(), original)
        self.assertIn("pending", configure.load_json(configure.sidecar(self.target)))
        self.cli("--profile", "docs", "--apply")
        self.assertNotIn("pending", configure.load_json(configure.sidecar(self.target)))
        self.cli("--profile", "minimal", "--apply")
        self.assertEqual(self.current(), self.original)

    def test_recovery_when_final_sidecar_write_fails(self):
        real = configure.atomic_write
        def fail_final(path, raw, **kwargs):
            if path == configure.sidecar(self.target) and "pending" not in json.loads(raw):
                raise OSError("injected finalization failure")
            return real(path, raw, **kwargs)
        with mock.patch.object(configure, "atomic_write", side_effect=fail_final):
            with self.assertRaises(OSError):
                self.run_direct()
        self.assertIn("context7", self.current()["mcpServers"])
        before = self.snapshot()
        self.cli("--profile", "minimal")
        self.assertEqual(self.snapshot(), before)
        self.cli("--profile", "minimal", "--apply")
        self.assertEqual(self.current(), self.original)
        self.assertNotIn("pending", configure.load_json(configure.sidecar(self.target)))

    def test_interrupted_transaction_with_external_edit_fails_closed(self):
        state = configure.state_document(self.target, {})
        state["pending"] = {"before": configure.digest(b'{}'), "after": configure.digest(b'[]'), "managed": {}}
        configure.sidecar(self.target).write_bytes(configure.encoded(state))
        before = self.snapshot()
        self.cli("--profile", "minimal", "--apply", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_journal_failure_never_changes_target(self):
        original = self.target.read_bytes()
        with mock.patch.object(configure, "atomic_write", side_effect=OSError("journal failed")):
            with self.assertRaises(OSError):
                self.run_direct()
        self.assertEqual(self.target.read_bytes(), original)
        self.assertFalse(configure.sidecar(self.target).exists())

    def test_change_after_planning_is_not_overwritten(self):
        before = self.target.read_bytes()
        changed = b'{"user":"changed"}'
        self.target.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "changed during planning"):
            configure.apply_plan(self.target, before, None, self.original, {}, {}, {})
        self.assertEqual(self.target.read_bytes(), changed)
        self.assertFalse(configure.sidecar(self.target).exists())

    def test_profile_conflict_is_all_or_nothing(self):
        self.cli("--profile", "docs", "--apply")
        data = self.current()
        data["mcpServers"]["exa"] = {"command": "user-owned"}
        self.target.write_text(json.dumps(data), encoding="utf-8")
        before = self.snapshot()
        self.cli("--profile", "web-research", "--apply", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_prime_wrapper_uses_same_ownership_path(self):
        wrapper = SCRIPT.with_name("sync-to-prime.py")
        def run(*args):
            result = subprocess.run([sys.executable, str(wrapper), "--target", str(self.target), *args],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        run("--profile", "docs", "--apply")
        self.assertEqual(self.current()["mcpServers"]["context7"]["env"]["CONTEXT7_API_KEY"],
                         {"env": "CONTEXT7_API_KEY"})
        run("--profile", "minimal", "--apply")
        self.assertEqual(self.current(), self.original)

    def test_profiles_and_prime_translation(self):
        expected = {"minimal": [], "code-graph": ["codebase-memory"], "ide": ["mcp-steroid"],
                    "docs": ["context7"], "repository-research": ["deepwiki"],
                    "web-research": ["exa"], "historical-context": ["openviking"]}
        for profile, names in expected.items():
            self.assertEqual(configure.selection(profile, None)[0], names)
        self.assertNotIn("code", configure.load_json(configure.PROFILES)["profiles"])
        self.cli("--profile", "docs", "--format", "prime", "--apply")
        server = self.current()["mcpServers"]["context7"]
        self.assertEqual(server["env"]["CONTEXT7_API_KEY"], {"env": "CONTEXT7_API_KEY"})
        self.assertNotIn("lifecycle", server)
        self.assertEqual(configure.translate({"type": "remote", "url": "fixture"}, "prime")["type"], "http")
        with self.assertRaises(ValueError):
            configure.translate({"env": {"VALUE": "literal"}}, "prime")
        self.cli("--profile", "unknown", ok=False)
        self.cli("--server", "unknown", ok=False)
        self.cli("--profile", "docs", "--server", "exa", ok=False)


if __name__ == "__main__":
    unittest.main()
