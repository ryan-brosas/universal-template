<!-- capsule-v2 -->
# Native binding loader — how do you load a platform-specific native addon with validation, caching, and a clean unsupported-platform error?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the contract for resolving/validating/caching per-platform native bindings behind one interface?

## Native loader
**Path/Symbol:** `src/live/native.ts` whole; package table :45-51; `validateLiveNativeBindings` :69-82; `loadLiveNative` :84-107.
**Signature:** `loadLiveNative(requirePackage?): LiveNativeBindings`; `resolveLiveNativePackage(platform, arch): string | undefined`; `validateLiveNativeBindings(value: unknown): LiveNativeBindings`.
**Data Shape:** Required surface: `AudioCapture` ctor (sampleRate, callback), `LiveWebRtcPeer` ctor (3 callbacks), `deviceCheckGenerateToken()`, `__ompInstallTokioRuntime()`.

### Decisive source
```ts
if (cachedBindings && requirePackage === runtimeRequire) return cachedBindings; // default-require cache only
const packageName = resolveLiveNativePackage(process.platform, process.arch);
if (!packageName) throw new Error(
  `Live voice is not available on ${process.platform}-${process.arch}. Supported targets: ${...}`);
try { loaded = requirePackage(packageName); }
catch (cause) { throw new Error(`Unable to load ${packageName}: ${detail}`, { cause }); }
const bindings = validateLiveNativeBindings(loaded);
bindings.__ompInstallTokioRuntime();
```

**Flow:** map `${platform}-${arch}` → optional package → loud unsupported-platform error listing targets → require with cause-preserving wrap → structural duck-type validation of ALL FOUR members → install runtime once → cache.
**Invariant:** Cache ONLY when the caller didn't supply a custom loader (`requirePackage === runtimeRequire`) so tests injecting fakes never poison the real cache; the module NEVER throws on missing members silently — validation failure is a loud descriptive Error; original require cause is preserved via `{cause}`.
**Probe:** `tests/live-native.test.ts` (:10-13 package resolution incl. freebsd→undefined, :24 partial-binding rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "loadLiveNative validateLiveNativeBindings NATIVE_PACKAGES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the table→validate→init→cache ladder with the custom-loader cache bypass. Adapt package names and required surface. Omit the tokio-runtime installation (Rust-host detail).
