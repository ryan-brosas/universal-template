<!-- capsule-v2 -->
# Device-id identity ladder — how do you derive a stable anonymous user id across restarts without accounts, and degrade through every failure?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** what identity does anonymous product telemetry use when there is no login, and how does it survive missing filesystems, containerized ephemeral hosts, and MAC-lookup failures?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/telemetry/service.py` whole (141L) — `get_or_create_device_id` (:28-34), `_persisted_device_id` (:37-50), `_machine_fingerprint` (:53-62), `ProductTelemetry` (@singleton :65; init gate :78-101; capture/:103-107, _direct_capture/:109-123, flush :125-133, user_id property :135-141); `singleton` decorator `browser_use/utils.py:481-489`.
**Signature:** `get_or_create_device_id() -> str`; `_persisted_device_id() -> str | None`; `_machine_fingerprint() -> str | None`; `ProductTelemetry.capture(event: BaseTelemetryEvent) -> None`.
**Data Shape:** module global `_device_id: str | None` cache; device file at `CONFIG.BROWSER_USE_CONFIG_DIR/device_id`; fingerprint = `'bu_' + sha256(f'browser-use:{node}:{hostname}')[:32]`.

### Decisive source
```python
_device_id = os.environ.get('BROWSER_USE_DEVICE_ID') or _persisted_device_id() or _machine_fingerprint() or uuid7str()

def _persisted_device_id() -> str | None:
	try:
		if os.path.exists(DEVICE_ID_PATH):
			with open(DEVICE_ID_PATH) as f:
				return f.read().strip() or None        # empty file falls THROUGH the ladder
		new_device_id = uuid7str()
		tmp_path = f'{DEVICE_ID_PATH}.{os.getpid()}.tmp'  # per-pid tmp name
		... write ...
		os.replace(tmp_path, DEVICE_ID_PATH)           # atomic publish, no partial reads
		return new_device_id
	except Exception:
		return None                                    # unreadable FS is not an error

def _machine_fingerprint() -> str | None:
	node = uuid.getnode()
	if (node >> 40) & 0x01:   # multicast bit set => getnode() FAILED and returned random
		return None            # refuse to mint a stable id from randomness
	return 'bu_' + hashlib.sha256(f'browser-use:{node}:{socket.gethostname()}'.encode()).hexdigest()[:32]

class ProductTelemetry:
	def __init__(self):
		telemetry_disabled = not CONFIG.ANONYMIZED_TELEMETRY
		if telemetry_disabled: self._posthog_client = None      # EVERY method short-circuits on None
		else:
			self._posthog_client = Posthog(..., enable_exception_autocapture=True)
			if not self.debug_logging: logging.getLogger('posthog').disabled = True

	def _direct_capture(self, event):
		try:
			self._posthog_client.capture(distinct_id=self.user_id, event=event.name,
				properties={**event.properties, **POSTHOG_EVENT_SETTINGS})
		except Exception as e:
			logger.error(...)          # telemetry NEVER raises into the agent path
```
**Flow:** first capture → singleton resolves → `user_id` property lazily calls `get_or_create_device_id()` once and caches → ladder tries env override, then the persisted file (creating it atomically if absent), then a hardware-derived hash, then a fresh uuid7 → event properties merged with `{process_person_profile: True}` and posted via posthog's own background queue.
**Invariant:** the four-tier order is load-bearing: env (test/CI determinism) > persisted file (survives hardware changes within one config dir) > fingerprint (survives deleted config dirs, only when the MAC is REAL — the multicast-bit guard prevents a random getnode() fallback from masquerading as stable identity, LIVE PROBE: returns None on this host) > uuid7 (always succeeds). Every filesystem error degrades to None, never raises; disabled telemetry must make BOTH capture and flush no-ops; posthog's chatty logger is silenced unless debug logging is on.

**Probe:** executed live (repo .venv): fingerprint returned None here (guard fired); persisted id stable across two calls with the atomic file created; `BROWSER_USE_DEVICE_ID` env overrides persistence; `ProductTelemetry() is ProductTelemetry()` True with client None under ANONYMIZED_TELEMETRY=false; flush safe. Direct test: `tests/ci/infrastructure/test_config.py::TestLazyConfig::test_cloud_sync_inherits_telemetry` PASSED (BROWSER_USE_CLOUD_SYNC inherits ANONYMIZED_TELEMETRY when unset).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "get_or_create_device_id _persisted_device_id _machine_fingerprint ProductTelemetry capture flush ANONYMIZED_TELEMETRY", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the four-tier identity ladder and its degradation contract for any opt-out-able telemetry plane; adopt the per-pid tmp + `os.replace` atomic publish and the multicast-bit honesty check verbatim. Adapt the env var names, file location, and hash salt to your product. Omit the hardcoded posthog project key/host (product credentials).
