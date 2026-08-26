<!-- capsule-v2 -->
# Comment body sanitization allowlist — which tags survive into stored comments, and why forbid form elements in a text field?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the sanitize policy for user-authored rich comments, and where does it run?

## DOMPurify config as data + store-time enforcement
**Path/Symbol:** `packages/nocodb/src/helpers/sanitizeCommentBody.ts:sanitizeCommentBody` (whole 56L); consumer: `src/services/comments.service.ts`.
**Signature:** `sanitizeCommentBody(input: unknown): string`; exported `COMMENT_SANITIZE_CONFIG` (ALLOWED_TAGS 20, ALLOWED_ATTR [href,class,target,rel], FORBID_TAGS 15, ALLOWED_URI_REGEXP).
**Data Shape:** allowed tags = p/span/a/b/i/u/strong/em/br/ul/ol/li/code/pre/blockquote/h1–h6; URIs restricted to ^(https?|mailto):.

### Decisive source
```ts
FORBID_TAGS: [
  'form', 'input', 'button', 'select', 'textarea', 'script', 'style',
  'iframe', 'object', 'embed', 'link', 'meta', 'svg', 'math', 'base',
],
ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
...
export function sanitizeCommentBody(input: unknown): string {
  if (input == null) return '';
  return DOMPurify.sanitize(String(input), COMMENT_SANITIZE_CONFIG);
}
```
(:33–:56)

**Flow:** comment create/update paths call sanitizeCommentBody BEFORE persistence — anything outside the allowlist is STRIPPED at write time, so readers never need to re-sanitize. The explicit FORBID_TAGS list exists because some tags pass an allowlist's absence check ambiguously or get mangled by parsers: form/input/button/select/textarea would let a comment render interactive UI inside the app origin (clickjacking/CSRF surface), svg/math host foreign-content parser confusion, base/meta hijack relative URLs and page metadata.
**Invariant:** sanitize at the WRITE boundary exactly once; the config is EXPORTED DATA so other surfaces (documents, notifications) reuse the identical policy instead of drifting. href survives but its URI scheme is pinned to http(s)/mailto — javascript: URLs die here. Nullish input normalizes to empty string, never throws.
**Probe:** `cd packages/nocodb && grep -c "sanitizeCommentBody\|COMMENT_SANITIZE_CONFIG" src/helpers/sanitizeCommentBody.ts` (=3: import + export const + fn) and `grep -c "ALLOWED_URI_REGEXP" src/helpers/sanitizeCommentBody.ts` (=1) and `grep -rn "l sanitizeCommentBody" src/services --include="*.ts" -l` shows comments.service.ts as sole service consumer.
**Direct test:** none upstream for this helper — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "sanitizeCommentBody COMMENT_SANITIZE_CONFIG DOMPurify", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-boundary sanitization with the config-as-exported-data pattern and interactive-element forbids; adapt tag vocabulary to your editor's output; omit if comments are plaintext-only. Coverage caveat: grep-pinned only.
