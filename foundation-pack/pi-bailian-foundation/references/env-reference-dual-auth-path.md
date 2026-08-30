<!-- capsule-v2 -->
# Env-reference dual auth path — does a BYO-key provider actually require its interactive login?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** Can a provider register OAuth machinery AND work with zero login, so users who hate prompts can still use it?

## Three-method credential-supply seam

**Path/Symbol:** `src/index.ts` module header (:4-5), `API_KEY_ENV` (:26-30), default-export doc-comment Usage block (:150-153), registration wiring `apiKey: API_KEY_ENV` (:160/:174); corroborated by README Configuration :64-108.
**Signature:** `apiKey: "$BAILIAN_CODING_PLAN_API_KEY"` on BOTH `registerProvider` calls — a literal-`$` string the HOST resolves as an environment-variable reference, not a key literal.
**Data Shape:** three coequal supply paths per region: (1) `/login <provider-id>` → oauth handlers persist credentials; (2) `export BAILIAN_CODING_PLAN_API_KEY=sk-sp-…` → host resolves the `$` reference per request; (3) hand-written `~/.pi/agent/auth.json` entry (`"type":"oauth"`, both slots = key).

### Decisive source
```ts
 * Adds Alibaba Cloud Bailian Coding Plan as a provider for Pi Coding Agent.
 * Supports both environment variable and interactive /login setup.
 ...
/**
 * Environment variable for the Bailian Coding Plan API key
 * API keys start with 'sk-sp-' prefix
 */
const API_KEY_ENV = "$BAILIAN_CODING_PLAN_API_KEY";
 ...
 * Usage:
 * - Environment variable: export BAILIAN_CODING_PLAN_API_KEY=sk-sp-xxxxx
 * - Interactive login: /login bailian-coding-plan
```

README Method 2 (:88-93) shows the no-login path end-to-end:
```bash
export BAILIAN_CODING_PLAN_API_KEY=sk-sp-xxxxx
pi
```

**Flow:** extension registers ONE env-reference string plus full oauth handlers → user picks any of the three paths → env path never touches `loginBailian`; auth-file path is exactly the object `loginBailian` would have persisted; `/login` path produces it interactively. All three converge on the same wire behavior because `getApiKey(credentials)` reads stored slots while the host resolves `$VAR` when credentials are absent.
**Invariant:** login is OPTIONAL UX, not a setup requirement — the module works unauthenticated-configured via the env reference. The env-var string is deliberately identical for both region twins (one export serves either provider id). Honest boundary: resolution ORDER between an env reference and stored credentials is host-side and NOT visible in this repo; this capsule pins only the extension-side contract that all three paths are wired simultaneously.
**Probe:** NO upstream test exercises env-reference resolution (`test/exports.test.ts` merely checks the default export is a function) — recorded coverage caveat; anchors verified by direct reads of :4-5, :26-30, :150-153, :160/:174 and README :64-108. Runner BLOCKED this pass (no node_modules in read-only checkout); deterministic line-pinned evidence per Gate-5 fallback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "environment variable api key configuration without login optional auth", limit: 8, fields: ["signature", "lines"] });
```
Executed live at pin: total 5 — `validateApiKey` (42-62), `getApiKey` (120-122), test-local validator (14-34), `loginBailian` (69-108), `loginBailianCN` (113-115); has_more false. Retrieval CAVEAT: BM25 surfaces the key HANDLERS but cannot address the doc-comment contract or the unnamed default export carrying `apiKey: API_KEY_ENV` — address this seam by direct read of `src/index.ts:1-36` and `:136-184`.

## Verdict
Adopt simultaneous wiring of an env-var reference AND oauth handlers so interactive login becomes opt-in rather than mandatory for BYO-key services. Adapt the variable name and login-target ids to your service; document all three supply paths in your README. Omit any extension-side precedence logic between env and stored credentials — that arbitration belongs to the host, and faking it here would fork the contract.
