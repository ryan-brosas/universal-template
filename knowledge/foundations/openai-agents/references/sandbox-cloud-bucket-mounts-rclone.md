<!-- capsule-v2 -->
# Sandbox cloud-bucket mounts and rclone bootstrap — how do you mount cloud storage inside a remote sandbox without leaking credentials or piping remote scripts into a shell?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** Two providers, two mount philosophies — E2B FUSE-mounts rclone INSIDE the sandbox at activate time, Modal declares native cloud buckets at create time. How does each validate credentials, bootstrap its toolchain safely, and why does Modal's activate() return an empty list?

## Delegated FUSE mounts vs declared-at-create native mounts
**Path/Symbol:** `src/agents/extensions/sandbox/e2b/mounts.py:` `E2BCloudBucketMountStrategy` (:67–154, activate :85–105, restore_after_snapshot :128–141), `_ensure_fuse_support` (:30–56), `_FUSE_ALLOW_OTHER` (:20–25), `_assert_e2b_session` (:59–64); `src/agents/extensions/sandbox/_rclone.py:` `ensure_rclone` (:93–155), `_rclone_install_command` (:51–91), `_rclone_arch` (:29–46), `rclone_pattern_for_session` (:177–192), `_RCLONE_CHECKSUM_MISMATCH_EXIT = 86` (:9), `_RCLONE_SHA256_BY_ARCH` (:13–21); `src/agents/extensions/sandbox/modal/mounts.py:` `ModalCloudBucketMountStrategy` (:28–97, activate :41–55), `ModalCloudBucketMountConfig` (:16–26), `_build_modal_cloud_bucket_mount_config` (:99–210).
**Signature:** `async def activate(self, mount: Mount, session: BaseSandboxSession, dest: Path, base_dir: Path) -> list[MaterializedFile]`; `async def ensure_rclone(session: BaseSandboxSession) -> None`; `def _build_modal_cloud_bucket_mount_config(self, mount: Mount) -> ModalCloudBucketMountConfig`.
**Data Shape:** e2b pattern: `RcloneMountPattern(mode="fuse")` with `extra_args` tuned per session (`--allow-other --uid <uid> --gid <gid>`). Modal config: `ModalCloudBucketMountConfig(bucket_name, bucket_endpoint_url, key_prefix, credentials: dict|None, secret_name, secret_environment_name, read_only=True)`; credentials are provider env-name dicts (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` for S3+R2, `GOOGLE_ACCESS_KEY_ID`/`GOOGLE_ACCESS_KEY_SECRET` for GCS HMAC).

### Decisive source
```python
# e2b: credential boundary re-validated at activate AND restore, then FUSE + rclone
validate_mount_activation_credential_boundary(
    mount, self,
    manifest=getattr(getattr(session, "state", None), "manifest", None),
    mount_path=lambda: mount._resolve_mount_path(session, dest),
    provider_backend_id="e2b",
)
_assert_e2b_session(session)
if self.pattern.mode == "fuse":
    await _ensure_fuse_support(session)
await _ensure_rclone(session)
delegate = await self._delegate_for_session(session)
return await delegate.activate(mount, session, dest, base_dir)
```
and the pinned, checksum-verified rclone install (never a curl|bash):
```python
curl --fail --location --silent --show-error --proto '=https' --tlsv1.2      --output "$tmp_dir/$archive" "$url"
if ! printf '%s  %s\n' "$expected_sha256" "$tmp_dir/$archive" | sha256sum --check --strict -; then
    exit 86          # _RCLONE_CHECKSUM_MISMATCH_EXIT -> MountConfigError
fi
...
target_tmp="$(mktemp /usr/local/bin/.rclone.XXXXXX)"
install -m 0755 "$tmp_dir/unpacked/${archive%.zip}/rclone" "$target_tmp"
printf '%s\n' "$version_output" | head -n 1 | grep -Fx 'rclone v1.74.4'   # self-verify
mv -f "$target_tmp" /usr/local/bin/rclone                                 # atomic replace
```
and the modal strategy whose activate does nothing:
```python
async def activate(self, mount, session, dest, base_dir) -> list[MaterializedFile]:
    if type(session).__name__ != "ModalSandboxSession":
        raise MountConfigError(...)
    _ = (mount, session, dest, base_dir)
    return []        # native mounts ride Sandbox.create(volumes=...), nothing to do here
```

**Flow:** e2b mounts delegate to the shared `InContainerMountStrategy` after per-session pattern tuning: `rclone_pattern_for_session` appends `--allow-other` and probes `id -u; id -g` to add uid/gid so the FUSE mount is writable by the sandbox user. The FUSE preflight checks device + `/proc/filesystems` + fusermount binary, then a root shell ladder makes `/dev/fuse` accessible and sets `user_allow_other`. Session-type guards compare `type(session).__name__` (not isinstance) because the concrete session class lives in a sibling module and importing it would defeat the optional-dependency gate. `_assert_e2b_session` runs on every strategy entry point. Modal's strategy is the inverse: `validate_mount`/`_build_modal_cloud_bucket_mount_config` do the real work at manifest-parse and create time (per-mount-type credential mapping, `secret_name` XOR inline-credentials mutual exclusion enforced per mount type, GCS native-auth rejected when no HMAC keys exist), `Sandbox.create` receives the volumes, and activate/deactivate/teardown/restore are deliberate no-ops returning `[]`/None. `supports_native_snapshot_detach` returns False so the snapshot ladder unmounts nothing for modal native buckets.

**Invariant:** (1) Credentials never cross the sandbox boundary twice: the credential-boundary validator runs at activate AND at restore_after_snapshot, and modal enforces inline-credentials XOR named-secret per mount type. (2) Toolchain bootstrap is supply-chain safe: pinned version + per-arch sha256 + TLS-pinned curl + atomic install + post-install self-verification — a checksum mismatch is a distinct exit code (86) mapped to a typed MountConfigError, never a silent continue. (3) A mount strategy that cannot act at activate time must fail loud on the wrong session type and otherwise do nothing — never partially mount. (4) Optional-dependency boundaries are preserved by name-based session guards, not imports.

**Probe:** `tests/extensions/sandbox/test_e2b.py` — `test_e2b_ensure_fuse_uses_root_chmod` (:124), `test_e2b_ensure_rclone_installs_verified_release` (:144), `test_e2b_rclone_pattern_adds_fuse_access_args` (:182), `test_e2b_rclone_pattern_preserves_explicit_access_args` (:191), `test_e2b_session_guard_rejects_wrong_type` (:111); `tests/extensions/sandbox/test_rclone.py` — `test_rclone_install_command_pins_and_verifies_archive` (:45, ordering: verify-execution < verify-version < atomic-replace), `test_ensure_rclone_preserves_preinstalled_binary` (:66), `test_ensure_rclone_rejects_unsupported_architecture_before_install` (:75), `test_ensure_rclone_reports_checksum_mismatch` (:92); `tests/extensions/sandbox/test_modal.py` — `test_modal_sandbox_create_passes_modal_cloud_bucket_mounts` (:775), `test_modal_sandbox_create_passes_named_modal_secret_for_cloud_bucket_mount` (:813), `test_modal_cloud_bucket_mount_strategy_rejects_secret_environment_name_without_secret_name` (:1110), `test_modal_cloud_bucket_mount_strategy_rejects_mixed_inline_credentials_and_secret_name` (:1125), `test_modal_cloud_bucket_mount_strategy_rejects_gcs_native_auth` (:1145), `test_modal_runner_builds_s3_native_bucket_by_default` (:1168).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "cloud bucket mount strategy rclone fuse allow_other credential boundary secret_name checksum pinned install", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pinned-checksummed-atomic installer for ANY in-sandbox toolchain bootstrap (never curl|bash), and the credential-boundary re-validation at every mount entry point. Adopt the declared-at-create pattern when your provider supports native mounts — moving mount work to create time deletes the whole unmount/remount dance from the snapshot path. Adapt the per-mount-type credential mapping and the XOR rules to your provider's secret model. Omit the FUSE preflight if your sandboxes guarantee device access. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
