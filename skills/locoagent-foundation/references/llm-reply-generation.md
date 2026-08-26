<!-- capsule-v2 -->
# LLM reply generation — how do you call a chat-completions API from a browser workflow and fit the result to a platform limit?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a deterministic browser executor hand post content to an LLM and get back a bounded, platform-fitting reply?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/x-search-reply.ts`: env load (`:49-73`), `callDeepSeek` (`:210-241`), per-post generation (`:360-375`). Same call in `workflows/executors/linkedin-search-reply.ts` (`callDeepSeek`).
**Signature:** `async callDeepSeek(postContent): Promise<string>` — `fetch(baseUrl + '/chat/completions', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key }, body })`.
**Data Shape:** env keys `OPENAI_API_KEY` / `OPENAI_BASE_URL` (default `https://api.deepseek.com`) / `OPENAI_MODEL` (default `deepseek-v4-flash`); request `{ model, messages: [{system},{user}], max_tokens: 256, temperature: 0.8 }`; response `data.choices?.[0]?.message?.content ?? ''`.

### Decisive source
```ts
const DEEPSEEK_API_KEY  = envVars['OPENAI_API_KEY'] ?? ''
const DEEPSEEK_BASE_URL = envVars['OPENAI_BASE_URL'] ?? 'https://api.deepseek.com'
const DEEPSEEK_MODEL    = envVars['OPENAI_MODEL'] ?? 'deepseek-v4-flash'
if (!DEEPSEEK_API_KEY) { console.error('Missing OPENAI_API_KEY in .env'); process.exit(2) }
// ...
const content = data.choices?.[0]?.message?.content ?? ''
return content.trim()
// per post:
post.replyText = reply.slice(0, 280)   // fit the platform limit, don't trust the model
```

**Flow:** a tiny line-based `.env` parser (skip blanks/comments, split on first `=`, trim) loads provider vars at boot and fails fast (exit 2) if the key is missing → `callDeepSeek` builds a system+user message pair from a config-supplied system prompt (default: short thoughtful reply, no hashtags/emojis, same language as post) and a `max_tokens: 256` cap → on non-OK response it throws with the first 200 bytes of the body → on success it `.trim()`s the content and the CALLER re-fits it to the platform limit with `slice(0, 280)`.
**Invariant:** The platform's hard limit is enforced by the CALLER after generation, never trusted to the model or the API's `max_tokens`. The provider is OpenAI-compatible via env indirection — the executor never hard-codes a provider endpoint or model, so the same workflow runs against any `/chat/completions` server. A failed or empty generation degrades per-post (empty `replyText` ⇒ later step skips it as "no reply text generated") rather than aborting the run.
**Probe:** No direct test for this executor (coverage caveat — source-grounded). Deterministic probes: grep pins `max_tokens: 256` at `:220`, `slice(0, 280)` at `:369`, and the key-missing `process.exit(2)` at `:70-73`; `search_graph --name-pattern "callDeepSeek"` resolves it in BOTH x-search-reply and linkedin-search-reply (repo-wide convention).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "callDeepSeek chat completions OPENAI_API_KEY max_tokens", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt env-indirected OpenAI-compatible provider config with fail-fast on missing key, a small line-based `.env` reader, caller-side platform-limit enforcement, and per-item degrade on generation failure. Adapt the system prompt, the limit (280 here), and `max_tokens`. Omit nothing — caller-side `slice` is what keeps a verbose model from breaking the post.
