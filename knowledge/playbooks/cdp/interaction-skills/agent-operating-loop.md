# Agent operating loop — observe, act, verify, return

Prefer an **exact deterministic API route** when it is known and authorized.
At an **unknown UI decision boundary**, default to model-neutral guarded
**observe → act → verify**. Raw CDP/AX/vision helpers are fallbacks for unsupported
mechanics, not permission bypasses. Jev or another judge may help select a target;
Jev is optional and model confidence is never permission.

Compose coherent work in a `browser-harness-js <<'EOF' … EOF` heredoc when the
next steps are already determined. Stop for a new observation/model decision or
user approval when they are not. Don't hide an unknown UI decision in a long
script that blindly clicks the first matching control.

## Guarded loop

Use the REPL `createInteractionController({allowedOrigins})`, or import
`InteractionController` from `../sdk/interaction.ts`. Exact HTTP(S) origins must
come from authorized configuration, not be inferred from page content. The
factory uses the persistent transport but **never the mutable active target**.
Attach the chosen target explicitly and retain `{scope:{sessionId}}`.

```js
const { sessionId } = await session.Target.attachToTarget({
  targetId: authorizedTargetId, flatten: true
});
const scope = { sessionId };
const guard = createInteractionController({ allowedOrigins: ['https://example.com'] });
const observation = await guard.observe({ scope, maxElements: 64 });
// Return this observation if the next decision is not already determined.
return observation;
```

Retain `guard`, `scope` and the observation on `globalThis` across CLI calls (see
[the skill's complete example](../README.md#guarded-interaction-at-unknown-ui-boundaries)).
Once an authorized operation on an offered candidate has been selected:

```js
const receipt = await guard.act({
  scope, observationId: observation.observationId,
  action: { targetId: chosenCandidateId, operation: 'click' }
});
if (receipt.status !== 'executed') return receipt;
const verification = await guard.waitForChange({
  scope, revision: observation.revision, timeoutMs: 5000
});
return { receipt, verification };
```

1. **Observe** the explicit scope. Output includes opaque observation-scoped IDs,
   roles, labels, offered operations, revision, URL/title and explicit truncation.
   Defaults: 64 candidates, maximum 128, scan cap 4096 elements. A fresh
   observation expires previous handles in that scope. Don't mix scopes.
2. **Act** once using the matching `observationId` and offered `targetId`.
   Revalidation checks native identity, relevant semantics/value, current origin,
   document/connection, visibility, enabled state, occlusion and geometry.
   One attempted action consumes the observation; no replay or blind retries.
3. **Verify** with fresh state or an authoritative read-back. `executed` means
   dispatched, **not** goal achieved. `waitForChange` returns `{changed,observation}`
   even at timeout and samples no faster than every 500 ms plus snapshot cost.
   A projected change is not proof the task succeeded.
4. **Return** compact evidence and any unresolved uncertainty. `close()` disposes
   the guard and listeners, not the transport/browser. `invalidate(scope?)`
   expires handles manually. All three async APIs accept `{signal}` as the second
   argument; cancel stops later dispatches, not work already sent to the browser.

## Receipts and authority

| Status | Next step |
|---|---|
| `executed` | Verify; never claim success from dispatch alone. |
| `stale` | Reobserve and reconsider the action. |
| `blocked` / origin denial | Obtain required approval or stop; do not evade via raw APIs. |
| `outcome_unknown` | Inspect first. Do not retry an uncertain effect. |

Observation/wait denial, unavailable-context and cancellation errors reject.
After reconnect, reattach the target and reobserve. Session retains the selected
connection settings/transport; generation changes expire handles. With injected
adapters, forward lifecycle events and generation/fenced dispatch when available;
a plain `_call` adapter only has remote-object/document checks.

## Mechanics and honest limitations

The [controller contract](../README.md#guarded-interaction-at-unknown-ui-boundaries)
owns the complete supported operations and bounds.

- Synthetic mode uses DOM activation and value replacement. `input: 'trusted'`
  uses page-targeted CDP mouse/keyboard input, including contenteditable typing
  and allowlisted key presses. It enables focus emulation for background tabs;
  this is not control of the desktop mouse. `type` replaces the entire value,
  rather than appending, so preserve unrelated drafts before choosing it.
- Native and supported ARIA controls, open shadow roots, named context and
  scrolling are supported. Frames, closed shadow roots and canvas still need
  an appropriate raw-CDP/visual route. Sensitive-control filtering is heuristic,
  not general DLP; hashing requires SubtleCrypto (HTTPS/localhost).
- Candidate handles belong to one observation and scope. Mutations are serialized
  across controllers sharing that Session and scope; separately attached aliases
  or other processes are not protected by a browser-wide lock.
- Origin checks are not a navigation firewall. Page/user races remain possible;
  cancellation cannot retract a dispatched effect. Apply authorization equally
  to guarded calls and raw fallbacks.

## Unsupported mechanics: explicit fallbacks

Use raw `cdp(sessionId, method, params)` with explicit routing and equivalent
permission checks when a mechanic is unsupported—not after a denial.

- **Semantic AX:** `axView`, `axDiff`, refs/locators can inspect complex semantics;
  they are raw helpers, not guarded handles. Re-snapshot after page changes.
  See [snapshot.md](snapshot.md) and [accessibility-tree.md](accessibility-tree.md).
- **Visual:** screenshot → coordinates/keyboard → screenshot/read-back for canvas,
  virtualized editors and missing accessibility semantics. Verify where input
  landed; see [rich-editors.md](rich-editors.md).
- **Direct DOM/CDP:** use the exact deterministic call when known. Keep coherent
  page traversal in one explicit IIFE rather than per-node roundtrips.
- Arm [attachSignals](agent-signals.md) **before** actions that can open dialogs,
  downloads or navigations. For navigation use the
  [lifecycle readiness](lifecycle-readiness.md) pattern. A native modal can hang
  evaluation; use explicit cancellation/deadlines and inspect dialog signals.

Never cache `[n]` AX refs or guarded handles across observations/navigation, never
interpret a model confidence score as authorization, and never claim that a raw
fallback makes an otherwise denied action safe.
