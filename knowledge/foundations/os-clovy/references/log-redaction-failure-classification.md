<!-- capsule-v2 -->
# Log redaction + failure classification — what may reach a log line, and how does an error become actionable?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter streaming agent/tool output into host logs must guarantee no secret survives and every failure lands in a UI-consumable category.

## Sanitizer + classifier pair
**Path/Symbol:** `agent-runtime/src/sanitize.ts:sanitizeForLog` (:12-34), `errorMessage` (:36-39), `runtimeFailureDetails` (:50-82), `taggedRuntimeFailure` (:84-113).
**Signature:** `sanitizeForLog(value: unknown, depth = 0): JsonValue`; `runtimeFailureDetails(error: unknown): { message, category: "tool"|"provider"|"runtime"|"context"|"credits", code: string, retryable: boolean }`.
**Data Shape:** Sanitizer returns JSON-safe values only; classifier's `code` values are stable wire constants (`agent_context_exceeded`, `agent_credits_required`, `agent_provider_failed`, `agent_runtime_failed`, or the tagged `failureCode`).

### Decisive source
```ts
if (depth > 8) return "[truncated]";
// strings: five ordered replaces
.replace(BEARER_VALUE, "Bearer [redacted]")
.replace(KEY_VALUE, "[redacted]")                       // sk_/osk_ 12+ chars
.replace(NAMED_SECRET_QUOTED, (m,p,q)=>`${p}${q}[redacted]${q}`)
.replace(NAMED_SECRET_BARE, "$1[redacted]")
.replace(SENSITIVE_HEADER_VALUE, "$1[redacted]");       // authorization/cookie lines
// arrays/objects: slice(0,100); SENSITIVE_KEY.test(key) ? "[redacted]" : recurse

const tagged = taggedRuntimeFailure(error);   // walks .error/.cause, depth 8, seen-set
if (tagged) return { message, category: tagged.failureCategory /* tool|credits */,
  code: ..., retryable: tagged.retryable === true };
// else regex ladder on lowercased message:
//   context length/token limit → context, not retryable
//   402 / insufficient credits → credits, not retryable
//   provider|upstream|429|5xx|timeout|econn... → provider, retryable
//   fallthrough → runtime, retryable
```

**Flow:** Every log emission path (`RuntimeService.log`, engine `tool.started/completed` arguments+output, interruption arguments via `parsedToolArguments`) funnels through the sanitizer first. Classification prefers STRUCTURE over text: an error carrying `failureCategory:"tool"|"credits"` anywhere in its cause chain wins outright; regexes only classify untagged errors.
**Invariant:** Redaction is applied AFTER parsing structured values AND inside raw strings, so secrets embedded in tool output or error messages still die; `retryable` is true ONLY for provider/runtime categories; aborts are never classified (callers check `isAbortError` first and emit `run.cancelled` instead).
**Probe:** `agent-runtime/test/sanitize.test.ts` — "redacts named secrets embedded in error and shell-output strings", "separates provider, context, credit, and local runtime failures", "classifies tagged tool failures without exposing credentials". Executed live at pin (17/17).

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"redact secrets sanitize log failure classification", file_pattern:"agent-runtime/*" })
→ src.sanitize.sanitizeForLog Function sanitize.ts 12-34        (rank 1)
   src.sanitize.runtimeFailureDetails Function sanitize.ts 50-82
   src.sanitize.taggedRuntimeFailure Function sanitize.ts 84-113
```

## Verdict
Adopt the two-plane split (structural tagging beats message regex; redaction is recursive and bounded). Adapt the regex vocabulary to your secret shapes; keep the depth>8 / 100-entry bounds as DoS armor for hostile tool output. Omit the Clovy code constants if your host has its own taxonomy — but keep codes STABLE across versions because the UI keys off them.
