<!-- capsule-v2 -->
# Typed OAuth-client-flow error family — how do you give each OAuth failure mode its own instanceof-able class without letting the retry ladder swallow it?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What is the `authErrors.ts` family's structure — base-class mechanics, per-class payloads, and WHY none of them extend `OAuthError`?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/authErrors.ts` whole file (:1-224): `OAuthClientFlowError` (:22-54), `IssuerMismatchError` (:75-108), `RegistrationRejectedError` (:113-133), `InsecureTokenEndpointError` (:140-157), `AuthorizationServerMismatchError` (:187-204), `InsufficientScopeError` (:206-224). Graph nodes confirmed for all six (e.g. `typescript-sdk.packages.client.src.client.authErrors.OAuthClientFlowError`). Brand mechanics shared with cross-bundle-brands.md; throw-site context in auth-main-flow-ladder.md / step-up-scope-union.md.
**Signature:** base: `new OAuthClientFlowError(message)` + `static isInstance(value): value is InstanceType<T>`; concrete constructors: `IssuerMismatchError(kind: 'metadata'|'authorization_response', expected, received)`, `RegistrationRejectedError({status, body, submittedMetadata})`, `InsecureTokenEndpointError(tokenEndpoint)`, `AuthorizationServerMismatchError(recordedIssuer, currentIssuer)`, `InsufficientScopeError({requiredScope?, resourceMetadataUrl?, errorDescription?})`.
**Data Shape:** every class carries an own `mcpBrand` static (`mcp.<ClassName>`); messages JSON-stringify embedded values so AS/challenge-supplied control characters cannot forge log lines.

### Decisive source
```ts
// :22-54 — base: branded, never thrown directly
export class OAuthClientFlowError extends Error {
    static { Object.defineProperty(this, 'mcpBrand', { value: 'mcp.OAuthClientFlowError' }); }
    static override [Symbol.hasInstance](value: unknown): boolean { return brandedHasInstance(this, value); }
    static isInstance<T extends abstract new (...args: never[]) => unknown>(this: T, value: unknown): value is InstanceType<T> {
        if (typeof this !== 'function') {
            throw new TypeError('isInstance must be called on the class … for callbacks use `v => SdkError.isInstance(v)`');
        }
        return brandedHasInstance(this, value);
    }
    constructor(message: string) { super(message); this.name = new.target.name; stampErrorBrands(this, new.target); }
}
// :75-108 — kind-tagged issuer failure; `received` attacker-controllable on the RFC 9207 path
export class IssuerMismatchError extends OAuthClientFlowError {
    readonly kind: 'metadata' | 'authorization_response';
    readonly expected: string | undefined;
    readonly received: string | undefined;   // MUST NOT display to end users
    constructor(kind, expected, received) {
        const where = kind === 'metadata' ? 'authorization server metadata (RFC 8414 §3.3)' : 'authorization response (RFC 9207)';
        super(`Issuer mismatch in ${where}: expected ${JSON.stringify(expected)}, received ${JSON.stringify(received)}`);
        …
    }
}
// :187-204 — the ONLY runtime check left in SEP-2352
export class AuthorizationServerMismatchError extends OAuthClientFlowError {
    constructor(public readonly recordedIssuer: string, public readonly currentIssuer: string) {
        super(`Authorization server changed between redirect and callback (…) refusing to send authorization_code/code_verifier to a different token endpoint`);
    }
}
```

**Flow:** each behavior change (SEP-2468/837/2207/2350/2352) adds its dedicated class here so callers `instanceof`-dispatch on the failure mode instead of string-matching messages. The base is a forward-compat family guard — nothing throws it directly, and `instanceof OAuthClientFlowError` catches the whole family. The deliberate hierarchy decision: NONE of the five extend `OAuthError`, because `auth()`'s catch block retries exactly on `OAuthError` codes (invalid_client/unauthorized_client/invalid_grant) — a mix-up indication, a registration rejection, or a non-TLS token endpoint is FATAL or a config error, not a retryable credential problem, and staying outside that hierarchy keeps the retry path from swallowing it (`InsecureTokenEndpointError` is explicitly rethrown by the refresh branch instead of falling through to a fresh /authorize).

**Invariant:** brand strings are pinned one-per-class (`mcp.<ClassName>`) and cross-copy `instanceof` must agree across duplicated module instances (the brand, not prototype identity, carries the match); `isInstance` reads the caller's own brand via `this` so every subclass inherits a correctly-scoped guard, and a DETACHED call throws rather than silently matching nothing; `IssuerMismatchError.received` and every `InsufficientScopeError` field originate from untrusted input (attacker callback / resource-server challenge) and must be treated as such when displayed or logged. SOURCE QUIRK: the `InsufficientScopeError` docblock is misplaced — it sits stacked above `AuthorizationServerMismatchError`'s declaration, so IDE hover shows the wrong class's docs there.

**Probe:** `packages/client/test/client/errorBrandConformance.test.ts` :32-36 (export-surface walker finds ≥15 classes incl. OAuthClientFlowError), :38-47 (every exported error class owns an mcpBrand; empty allowlist), :71-87 (brand strings pinned exactly, incl. all five family members), :89-104 (isInstance agrees with instanceof over [plain Error, null, undefined, 0, '', {}]), :106-129 (cross-copy: vi.resetModules foreign import — `instanceof` and both `isInstance` guards agree across module copies, UnauthorizedError does NOT match the family); `packages/client/test/client/auth.test.ts` :5064-5085 (fail-closed gate message shape); `packages/client/test/client/streamableHttp.test.ts` :1156-1178 ('throw' mode rejects with InsufficientScopeError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "typescript-sdk", qualified_name: "typescript-sdk.packages.client.src.client.authErrors.AuthorizationServerMismatchError" });
```

## Verdict
Adopt the "typed family outside the retryable hierarchy" pattern verbatim — it is what makes auth()'s single-retry ladder safe; adopt the pinned-brand + detached-call-throws guard contract with cross-bundle-brands.md; adapt payload fields to your host's diagnostics needs; omit any plan to make these extend OAuthError "for convenience" — that silently re-enables credential-invalidation retries on fatal mix-up/config errors. Coverage caveat: the misplaced InsufficientScopeError docblock is a source defect at this pin, not a porting requirement.
