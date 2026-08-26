<!-- capsule-v2 -->
# Privacy scrubbing at capture — what may hit disk when a human types into a browser the agent drives?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How are passwords, credential URLs, and typed plaintext kept out of evidence files?

## URL secret regex + userinfo/path scrub + hash strip; typing fails closed to mask unless field PROVEN non-password
**Path/Symbol:** `skills/cdp/sdk/recording.ts:URL_SECRETS` (:45), `scrubUrl` (:164-178), `capture` text gate (:417-449).
**Signature:** `scrubUrl(value: unknown): string` · inside `capture`: `privateText` retained node-side only, `publicDetails` deletes `text`, disk decision made AFTER context eval.
**Data Shape:** masked placeholder is the literal `'••••••'` with flags `textRedacted: true`, `password: true`.

### Decisive source
```ts
const URL_SECRETS = /([?&#](?:code|access_token|id_token|refresh_token|token|assertion|client_secret|client_info|session_state|api_?key|sig|signature|auth|authorization|password|secret)=)[^&#]+/gi;
...
if (url.username) url.username = 'REDACTED';
if (url.password) url.password = 'REDACTED';
url.pathname = url.pathname.replace(/\/(token|secret|password|passcode|api[_-]?key)\/[^/]+/gi, '/$1/REDACTED');
url.hash = '';                       // fragments carry OAuth state / SPA session material
...
if (privateText !== undefined) {
  if (context.input && context.input !== 'password') {
    event.text = privateText;        // positively non-password → allowed on disk
  } else {
    // Fail closed when focused-element inspection is unavailable: never let
    // plaintext reach disk unless the field was positively non-password.
    event.text = '••••••'; event.textRedacted = true;
    if (context.input === 'password') event.password = true;
  }
}
```

**Flow:** classify the raw CDP call → capture page context (activeElement type/box) → scrub every URL-shaped value (query secrets, userinfo, secret-bearing path segments, fragment dropped wholesale) → typing events keep their text ONLY if inspection succeeded AND the focused field isn't password; otherwise write the fixed mask with redaction flags → append one 0600 JSONL line.
**Invariant:** FAIL CLOSED is the core rule: missing/failed context inspection must produce the MASK, not the plaintext — "unknown field" is treated like "password". Fragments are stripped unconditionally because they're never needed by the video compiler and routinely hold state. The same event carries `beforeFrame` so compositions can show pre-action state.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts`: `'recorder masks password text and scrubs credential URLs'` pins the exact scrubbed URL string and mask flags (:106-142); `'typed text fails closed when focused-element inspection fails'` asserts the plaintext NEVER reaches events.jsonl (:145-175).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "scrubUrl", limit: 3, fields: ["signature", "name", "file"] });
// resolves recording.classify's sibling surface; scrubUrl sits in recording.ts:164-178 (graph indexes the module)
```

## Verdict
Adopt fail-closed masking + layered URL scrubbing for ANY agent that records user-visible browsing; adapt the secret-key list to your threat model; omit nothing here without accepting that your evidence files become a credential store.
