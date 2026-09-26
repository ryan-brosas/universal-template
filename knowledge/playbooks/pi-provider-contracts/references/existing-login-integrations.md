# Reuse host logins across SDK and MCP backends

Use when an SDK integration or backend migration should consume logins the host
already manages, including direct and gateway routes to the same model family.
For example, `/login jev` and `/login openrouter` are separate account identities,
not interchangeable keys. Start by checking the existing login path, not by
proposing another environment variable, keyring entry, or login.

## Map identity before choosing transport

Separate three facts: the host's **auth provider ID**, the SDK's **endpoint and
protocol**, and the request's **model ID**. Read the installed host resolver and
provider registration, then the selected service's current SDK documentation.
The model's name alone identifies neither its credential nor its transport.

A miss in an ordinary chat-model catalog does not establish that a dedicated SDK
route is unavailable. Check documented support and use a bounded authorized
probe; do not invent an endpoint or force typed judgments through chat. Likewise,
a documented route is not proof that the current account can use it.

## Reuse the resolver, not the secret

Keep credential resolution host-owned. Capture the appropriate session-scoped
service before asynchronous work, not a resolved key or a context that may become
stale. Use its supported resolver for each enabled, permitted evaluation so the
host controls refresh, rotation and logout. Do not read the credential file
directly or copy keys into adapter config, subprocess environments, or logs.
Disabled or policy-denied work should not resolve credentials or call the service.

Distinguish a missing login from a configured login that cannot resolve. Preserve
only the documented same-provider fallbacks; do not silently bypass a broken
stored credential. Switching to a gateway selects that gateway's login, not the
direct service's fallback key. Bind each resolved credential to the selected
route's approved destination, not a union of all supported providers' origins.
Apply the owning playbook's redirect and wire-security checks.

Normalize documented gateway envelope additions separately from typed answers.
Accepting request metadata must not weaken answer, usage, or error validation.

## Prove the loaded path and the backend used

Preserve existing defaults, public tool references, approval and data-sharing
boundaries when swapping MCP backends. Test the new route and the unchanged route;
a build or a listing of registered tools does not establish migration readiness.

Use synthetic credentials for focused tests of destination pairing, rotation,
logout, missing versus unavailable auth, disabled work, and malformed responses.
Then exercise the actual extension host. A bare runtime can omit a provider
registered by an extension; first confirm registration and the facade under test
before diagnosing a credential as missing. Reload or start a fresh process when
source or configuration changed after startup.

Capture a compact structured receipt from the tool/runtime: requested backend,
backend used, selected provider, returned model, degradation reason, and relevant
usage. Use nonempty candidate input and confirm an outbound evaluation occurred:
a successful no-candidate short circuit can report a semantic backend without
calling it. Returned tool references alone can come from lexical fallback.

Parse the actual result envelope, including a nested JSON string when present,
rather than searching model-rendered prose or guessing from missing grep hits.
Recover the saved receipt before repeating a paid canary because output was
escaped or truncated. Keep the command's real exit status when filtering logs.
Report default-path and alternative-path evidence separately, with unresolved
findings intact. For broader-suite failure attribution, use the existing
[debugging guidance](../../debugging-and-error-recovery/README.md); a passing
isolated rerun does not establish why the original run failed.
