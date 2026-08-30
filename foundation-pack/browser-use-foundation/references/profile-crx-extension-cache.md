<!-- capsule-v2 -->
# Default-extension CRX cache pipeline — download-once, verify MV3, patch storage, degrade per-extension

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How do you auto-provision Chrome extensions (ad-blocker, cookie-handler) at launch without failing the whole launch when the web store is unreachable?

## _ensure_default_extensions_downloaded(): per-extension try/continue ladder
**Path/Symbol:** `browser_use/browser/profile.py:_ensure_default_extensions_downloaded` (1010-1104), `_extract_extension` (1181-1233, CRX header skip), `_check_extension_manifest_version` (991-1008), `_apply_minimal_extension_patch` (1106-1168), `_get_extension_args` (975-989).
**Signature:** `def _ensure_default_extensions_downloaded(self) -> list[str]`
**Data Shape:** cache dir `CONFIG.BROWSER_USE_EXTENSIONS_DIR`, layout `<cache>/<ext-id>/{manifest.json,...}` + `<cache>/<ext-id>.crx`. Returns list of extracted dir paths; each failure logs a warning and CONTINUES.

### Decisive source
```python
if ext_dir.exists() and (ext_dir / 'manifest.json').exists():
    if not self._check_extension_manifest_version(ext_dir, ext['name']):
        continue            # cached but MV2 => silently excluded
    extension_paths.append(str(ext_dir)); continue
try:
    if not crx_file.exists():
        self._download_extension(ext['url'], crx_file)
    self._extract_extension(crx_file, ext_dir)
    if not self._check_extension_manifest_version(ext_dir, ext['name']):
        continue
    extension_paths.append(str(ext_dir))
except Exception as e:
    logger.warning(f'⚠️ Failed to setup {ext["name"]} extension: {e}')
    continue                # one bad extension never blocks the launch
...
# CRX files have a header before the ZIP data
magic = f.read(4)
if magic != b'Cr24': raise Exception('Invalid CRX file format')
version = int.from_bytes(f.read(4), 'little')
if version == 2:  ... f.seek(16 + pubkey_len + sig_len)
elif version == 3: header_len = ...; f.seek(12 + header_len)
```

**Flow:** fixed table of {name, chrome-store id, crx3 URL} → per ext: reuse extracted dir (after MV3 check) else download .crx else use cached .crx → extract (try plain ZIP; on BadZipFile parse Cr24 header v2/v3 and slice to ZIP payload) → MV3 gate → collect path → AFTER loop, string-patch the cookie extension's `background.js` to inject an `ensureWhitelistStorage()` pre-populating `chrome.storage.local.settings.whitelistedDomains` from `cookie_whitelist_domains` → `_get_extension_args` emits `--load-extension=` + throttling/activity flags.
**Invariant:** per-extension isolation (try/except/continue) — the launch proceeds with zero extensions rather than failing; MV2 manifests are dropped BOTH for cached and freshly-extracted dirs (Chrome 145+ rejects them); the JS patch must be idempotent-shaped (only replaces the exact legacy `initialize()` body; absent pattern = debug-log, not error).
**Probe:** deterministic source pin: `grep -n "Cr24" browser_use/browser/profile.py` (:1209) and `"Failed to setup"` (:1091). Coverage caveat: network download path untested upstream; manifest-version check verified by reading.
**Retrieve note:** graph anchors resolve under `browser-use.browser_use.browser.profile`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_ensure_default_extensions_downloaded _extract_extension", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cache-dir + per-item degradation + format-header recovery for any auto-provisioned binary asset; adapt extension ids/URLs (they rotate); omit the commented-out candidate extensions. The storage-prepopulation patch is adoptable only if you also ship the matching extension build.
