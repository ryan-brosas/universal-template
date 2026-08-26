<!-- capsule-v2 -->
# Reuse map — which localterm primitives port to another harness, and which mistakes do they prevent?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What is the full inventory of reusable contracts in this repo, each with its one-line invariant and its canonical trap?

## Portable primitives by subsystem (every entry verified at HEAD this session)
**Path/Symbol:** see per-seam capsules for line ranges; graph boundaries: terminal→server (37), cli→server (29), server→pi-extension (20); hotspots: cn (108), runGit (26), bash-secret-scrub emit (23), onClose (19), identity/resolve (18), fetchSessionApi (18).

### Security / secrets
- `createStreamingRedactor` + `overlapTailLen` + `redactText` (`packages/pi-extension/src/utils/redact-output.ts`) — stream-safe exact-value redaction. **Trap:** emitting the overlap tail leaks a split value's head; masking with a length-preserving char leaks length.
- `scrubEnv` (`scrub-env.ts`) — pure, non-mutating child-env strip. **Trap:** letting spawned commands inherit `{...process.env}` exposes every injected secret to `env`/`printenv`.
- Policy chain (`read-localterm-secret-policy.ts` + `read-secret-values.ts`) — names-only files, values from process.env, canonical patterns. **Trap:** reading secret VALUES from disk policy files.
- `readPiShellSettings` — settings passthrough on tool override. **Trap:** overriding a built-in tool without re-baking user config.
- `encryptSecretExport`/`decryptSecretExport` (`packages/server/src/secret-export.ts:13–41`) — age passphrase encryption + armor (versioned payload `SECRET_EXPORT_VERSION = 1`, scrypt work factor 2^18, constants.ts:209/217); zod fail-closed validation; interoperable with stock `age -d -p`. **Trap:** a custom format that locks users out of their own secrets.
- `isLoopbackHost`/`isPrivateHost`/`createNetworkPolicyMiddleware`/`isAllowedSourceIp` (`packages/server/src/security.ts`) — host-header stripping, bare-IPv6 bracketing, private ranges (10/172.16–31/192.168/100.64–127/127/169.254), `.localhost` suffix, DNS-rebind rejection, tailscale public-origin exemption. Probe: `tests/security.test.ts` :70 forged Host rejected.

### Terminal / PTY
- Session lifecycle + out-of-band title/cwd/foreground channels + mode-restored 256KB scrollback replay (`packages/server/src/session.ts`). **Trap:** splicing OSC sequences into the output stream corrupts DECSET 2026 synchronized frames.
- Coordinator/transport with water-mark flow control, atomic-vs-progressive framing, typed-header compression (`session-output-coordinator.ts`, `session-output-transport.ts`). **Trap:** an unbounded PTY→WS pipe balloons memory or dies mid-redraw.
- Kitty APC scanner + daemon-side probe answering + straddle-safe reset detection (`kitty-apc-scanner.ts`, `kitty-frame-file-relay.ts`). **Trap:** leaking medium probes races the emulator's own reply.
- Env builder + shell hooks (`build-pty-environment.ts`, `shell-hook-builder.ts`). **Trap:** leaking `TERM_PROGRAM=ghostty` degrades Ink TUIs to inline-plain.

### Git
- Diff service/parser/cache/watcher (`git-diff*.ts`) — three parallel invocations keyed by path, capped untracked synthesis. **Trap:** positional pairing of numstat↔patch blocks breaks on symlink-re-add paths; untracked patches need the `\ No newline` marker.
- `reverseUnifiedPatch` (`apps/harness/light-theme-rendering/reverse-unified-patch.mjs`) — verify-or-throw undo. **Trap:** reversing without checking context lines silently corrupts.

### Agent integration
- Capability-before-first-query (`extensions/kitty-images.ts`), settle+elapsed-gated OSC 9 notify (`agent-notify.ts`, `osc-sequence.ts`), bash-tool reconstruction with settings passthrough (`bash-secret-scrub.ts`). **Traps:** enabling images after TUI.start() skips the first CSI 16 query; notifying before settle is stale; OSC bodies that split surrogates.
- Marker-token exec in a shared interactive PTY (`session-command-executor.ts:116–260`) — random start/end markers chained on ONE input line, exit code parsed from the raw stream, timeout commits → Ctrl-C → 500ms grace ignoring late markers, fresh-renderer extraction. **Trap:** scraping the prompt or using the shell's own exit as the command's status.
- Event-driven wait ladder (`session-command-executor.ts:29–90`) — text/regex with up-front eval on output events, recency-based idle poll (no per-tick renderer read), exit-aware timeout through one idempotent finalize. **Trap:** deciding matches on stale grid state without flush-before-read, or polling raw bytes instead of the ANSI-rendered pane.

### Measured thresholds worth stealing (constants.ts)
- Flow control: pause ≥4MB / resume ≤1MB / poll 50ms / kill at 64MB; pending client caps 4MB bytes / 256 control messages.
- Framing: 64K chunks (measured 4–6ms parse under xterm's 12ms budget; ~235 msg/s vs ~470 at 32K because per-message task-lifecycle overhead dominates), 2ms idle window, 100ms stream classifier, 1000ms DEC 2026 safety timeout.
- Compression: 0x00 raw / 0x01 gzip / 0x02 brotli / 0x03 brotli-ctx (5-byte header + LE raw size). Brotli q6 ~10× per 64K chunk; ctx-takeover delta 1.24–3.7× (3.7× = 1-row TUI update).
- Bounds: MAX_INPUT 64K / MAX_OUTPUT 1MB / image upload 32MB (+64K multipart) / title 4K / notification 1024 / cols·rows ≤1000 / sessions ≤64 / kitty keyboard stack depth 16.

### Omitted-with-reason from the portable set
Daemon lifecycle stores (update-check/heartbeat/automation/worktree-config), caffeinate keep-awake family, CDP browser viewer, CLI installers (launchd/systemd), React terminal app, xterm-bench suite — host-specific product plumbing, not reusable contracts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "createStreamingRedactor|reverseUnifiedPatch|isPrivateHost|SessionOutputTransport|ShellHookBuilder", limit: 10 });
```

## Verdict
Adopt the primitive contracts above as a menu — each is independently portable behind its capsule's invariants; adapt every host-specific integration point (pi extension API, macOS Keychain, vite-plus tests, node-pty) to your environment; omit the product surfaces listed above unless building the whole hub. Coverage caveat: all probes cite on-disk vite-plus test files (excluded from the graph index by design).
