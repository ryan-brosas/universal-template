<!-- capsule-v2 -->
# Device-target registry with blank-means-default resolution — how do desktop/iOS/android map to agent-browser emulation profiles without a second config dialect?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How should a logical device target (desktop vs mobile emulation) be resolved from env and translated into CLI args, so a blank `.env` placeholder cannot crash bring-up?

## Three-entry DEVICE_REGISTRY + pure resolver
**Path/Symbol:** `scripts/lib/device.ts`:`DEVICE_REGISTRY` (`:15-19`), `isDeviceTarget` (`:21-23`), `resolveDevice` (`:26-36`), `agentBrowserProfileArgs` (`:39-42`); consumers `config.ts:loadConfig`, `setup-chrome.ts`, `doctor.ts`.
**Signature:** `resolveDevice(env?: NodeJS.ProcessEnv): DeviceTarget`; `isDeviceTarget(v: string): v is DeviceTarget`; `agentBrowserProfileArgs(target: DeviceTarget): string[]`.
**Data Shape:** `DeviceTarget = 'desktop' | 'ios' | 'android'`; `DeviceSpec { abProfile: string | null, label: string }` — `desktop.abProfile === null` means NO emulation flags; ios/android map to agent-browser `-p ios|-p android` profiles.

### Decisive source
```ts
/** Resolve the active device target from env (DEVICE_PROFILE), default desktop. */
export function resolveDevice(env: NodeJS.ProcessEnv = process.env): DeviceTarget {
  // A blank/whitespace DEVICE_PROFILE (e.g. an empty `.env` placeholder) means
  // "use the default", not an invalid target — fall back to desktop.
  const raw = (env.DEVICE_PROFILE ?? '').trim().toLowerCase() || 'desktop'
  if (!isDeviceTarget(raw)) {
    throw new Error(
      `Invalid DEVICE_PROFILE "${raw}". Valid values: desktop, ios, android.`,
    )
  }
  return raw
}
export function agentBrowserProfileArgs(target: DeviceTarget): string[] {
  const spec = DEVICE_REGISTRY[target]
  return spec.abProfile ? ['-p', spec.abProfile] : []
}
```

**Flow:** read `DEVICE_PROFILE` → trim + lowercase → empty string is falsy so `|| 'desktop'` absorbs blank/whitespace → type-guard rejects unknown values with a throw that lists valid values → registry lookup turns the target into zero or two CLI args (`[]` for desktop, `['-p','ios']` for mobile). The agent runs on a desktop host; iOS/Android are browser *emulations* via agent-browser device profiles, not native runtimes.
**Invariant:** Blank ≠ invalid. The same normalization contract as `pick()` in `config.ts` (blank `.env` placeholder ⇒ default, unknown value ⇒ loud throw) applied to a third env var. A porter who treats `DEVICE_PROFILE=` as the literal empty string produces `Invalid DEVICE_PROFILE ""` and bricks bring-up on machines that ship placeholder `.env` files. Desktop must stay a real registry entry with `abProfile: null` (not a missing key) so `agentBrowserProfileArgs('desktop')` returns `[]`, never undefined.
**Probe:** `scripts/lib/device.test.ts` — `resolveDevice defaults to desktop` (:10), `reads DEVICE_PROFILE (case-insensitive)` (:14, `'iOS'` ⇒ `ios`), `rejects unknown values` (:18), `treats a blank DEVICE_PROFILE as desktop` (:24, both `''` and whitespace), `agentBrowserProfileArgs returns -p flags` (:29). Bun-run blocked on this host (no Bun runtime); assertions read and pinned from the on-disk test source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "resolveDevice|isDeviceTarget|agentBrowserProfileArgs|DEVICE_REGISTRY", limit: 10 });
```
Graph confirms all four symbols line-exact (`device.ts` :15/:21/:26/:39); inbound callers: loadConfig, resolveTarget, setup-chrome, doctor (trace_path, 9 callers).

## Verdict
Adopt the registry-of-three shape (null profile ⇒ no args), trim+lowercase+`||default` env resolution, and the list-valid-values error message. Adapt profile names to your automation CLI's device-emulation vocabulary. Omit native-mobile runtimes — this abstraction deliberately scopes to browser emulation only.
