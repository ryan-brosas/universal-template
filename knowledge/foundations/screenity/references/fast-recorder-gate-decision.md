<!-- capsule-v2 -->
# Fast-recorder gate decision — who wins when user setting, sticky disable, and probe disagree?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** When a porter combines an opt-in beta flag, a per-device failure ban, and a capability probe, what is the exact precedence so a stuck device can still be force-re-enabled?

## Gate decision tri-state ladder
**Path/Symbol:** `src/media/fastRecorderGate.ts:816-824` (`shouldUseFastRecorder`), with `resolveFastRecorderUserSetting` :812-814.
**Signature:** `shouldUseFastRecorder(userSetting: boolean | null | undefined, probeResult: FastRecorderProbeResult, stickyDisableState: FastRecorderStickyState) => boolean`.
**Data Shape:** `userSetting` is the raw storage value coerced by `resolveFastRecorderUserSetting` to `true|false|null` (anything not boolean → null); probe carries `{ok, reasons, details.selectedVideoConfig}`; sticky state `{disabled, reason?, details?}`.

### Decisive source
```ts
// Unset must stay null: shouldUseFastRecorder lets an explicit `true` override
// a sticky disable, so folding unset into true makes the disable unreachable.
export const resolveFastRecorderUserSetting = (
  raw: unknown
): boolean | null => (raw === true ? true : raw === false ? false : null);

export const shouldUseFastRecorder = (
  userSetting: boolean | null | undefined,
  probeResult: FastRecorderProbeResult,
  stickyDisableState: FastRecorderStickyState
) => {
  if (userSetting === false) return false;
  if (stickyDisableState?.disabled && userSetting !== true) return false;
  return probeResult?.ok === true && Boolean(probeResult?.details?.selectedVideoConfig);
};
```

**Flow:** explicit user OFF → false (beats everything) → sticky disabled and user did NOT explicitly re-enable → false → else require probe ok AND a selected encoder config (a config-supported "yes" without a chosen config is not enough).
**Invariant:** `null`/`undefined` opt-in state must never behave like `true`, or the self-healing sticky-disable could never take effect on default users; conversely an explicit `true` must override the sticky ban (user intent outranks heuristics).
**Probe:** no upstream tests exist at pin (`tests/` untracked). Deterministic anchor: grep `src/media/fastRecorderGate.ts` for `Unset must stay null` (:810) and `probeResult?.details?.selectedVideoConfig` (:823) — byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
search_graph(project="screenity", name_pattern="^(shouldUseFastRecorder|resolveFastRecorderUserSetting)$")
→ observed: 2 rows, screenity.src.media.fastRecorderGate, lines 812-814 / 816-824 (exact match at pin)
```

## Verdict
Adopt the three-way precedence and the unset-stays-null coercion verbatim — it is the whole point of the seam. Adapt storage key names and where the probe/sticky inputs are loaded. Omit the `fastRecorderBeta` product naming.
