<!-- capsule-v2 -->
# CDP stack freeze pass — how can page JS be hardened against stack-based CDP leak checks (and is it actually wired)?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** what does `cdpDetectionPass` freeze, and where does it belong in the launch pipeline?

## Init script locks Error.prototype.stack and freezes instances — but is never invoked at this pin
**Path/Symbol:** `shared/server/bots/cdp.detection.pass.ts:cdpDetectionPass` (:3-33).
**Signature:** `(page: Page) => Promise<void>` — single `page.addInitScript(...)` call.
**Data Shape:** none; pure page-side mutation before any document script runs.

### Decisive source
```js
Object.defineProperty(Error.prototype, 'stack', {
    configurable: false, enumerable: true, writable: false,
    value: (() => { try { throw new originalError(); } catch (e) { return e.stack; } })()
});
window.Error = new Proxy(originalError, {
  construct(target, args) { return Object.freeze(new target(...args)); }
});
```

**Flow:** at document-start the real `Error.prototype.stack` is replaced by a NON-configurable, non-writable snapshot of one genuine stack; `new Error(...)` returns frozen instances, so automation-detection scripts that overwrite/normalize `stack` to compare against driver fingerprints (CDP/patchright leaks surface as synthetic stacks) can no longer tamper per-instance.
**Invariant:** verified at this pin: `grep -rn 'cdpDetectionPass' --include='*.ts' .` matches ONLY its definition file — no call site in BotManager.launch/getContext/runProcess or anywhere else. The reference-note claim ("BotManager.launch → cdpDetectionPass(page) → provider actions") does NOT hold at HEAD `abb1e37a`: it is prepared but UNWIRED. A porter must wire it explicitly after context creation (and note it hardens only stack-based checks — not a full stealth layer).
**Probe:** no test runner upstream. Deterministic pins: definition `search_graph --project growchief --query cdpDetectionPass` → cdp.detection.pass.ts:3-33; absence `grep -rn 'cdpDetectionPass(' shared/server apps | grep -v 'export const'` → empty.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "addInitScript Error stack", limit: 5 });
```

## Verdict
Adopt the technique (freeze stack accessor + instance-freeze constructor proxy) for any driver-leak hardening question; ADAPT by wiring it yourself in the right lifecycle slot. Omit the assumption that it is active in growchief's pipeline — record says otherwise.
