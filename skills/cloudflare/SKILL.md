---
name: cloudflare
description: Use when deploying to or configuring ANY Cloudflare service, Workers, Pages, KV, D1, R2, AI, Tunnel, WAF. MUST load before writing Cloudflare Workers code, wrangler configs, or infrastructure-as-code for Cloudflare.
disable-model-invocation: true
---


# Cloudflare

## Core Principle

Workers are V8 isolates, not Node.js, the edge runtime is small, fast, cold; secrets via `wrangler secret put`, bindings over fetch.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **Workers are V8 isolates, not Node.js.** No `fs`, no `child_process`, no `Buffer` (use `Uint8Array`).
- **Edge runtime = small, fast, cold.** Keep bundles small. No kitchen sink imports.
- **Secrets via `wrangler secret put`**, never in `wrangler.toml`. Never in code.
- **Compatibility flags** for Node APIs (`nodejs_compat`, `nodejs_compat_v2`).
- **Bindings over fetch.** Use D1/R2/KV bindings, not HTTP to own services.
</EXTREMELY-IMPORTANT>

## When to Use

Writing Workers; configuring `wrangler.toml`; bindings (KV, D1, R2, Queues); Pages; Workers AI; Tunnels; WAF; DNS; any Cloudflare infra.

## When NOT to Use

Plain Node.js server (no CF); static without Workers; different platform.

## Workflow

1. Pick the service from the Core Services table.
2. Write the Worker with a typed `Env` binding contract.
3. Declare bindings in `wrangler.toml`; put secrets via `wrangler secret put`.
4. Iterate with `wrangler dev` (`--local` for fast iteration, `--remote` for actual Cloudflare bindings).

## Core Services

| Service | Use |
|----------------|-----------------------------------------------|
| **Workers** | Compute at the edge (V8 isolate) |
| **Pages** | Static + Workers Functions |
| **KV** | Low-latency key-value (eventually consistent) |
| **D1** | SQLite at the edge |
| **R2** | S3-compatible, no egress fees |
| **Queues** | Async messaging |
| **Workers AI** | Run models on Workers |
| **Vectorize** | Vector DB for similarity search |
| **Tunnel** | Secure origin connectivity |
| **WAF** | Web app firewall rules |
| **DNS** | Authoritative DNS |

## Workers Code Anatomy

```ts
export interface Env {
  DB: D1Database
  BUCKET: R2Bucket
  KV: KVNamespace
  AI: Ai
}

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    // ...
  }
}
```

`Env` is the contract. Bindings typed via Cloudflare's type defs.

## wrangler.toml (config)

```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2025-01-01"
compatibility_flags = ["nodejs_compat"]

[[kv_namespaces]]
binding = "KV"
id = "..."

[[d1_databases]]
binding = "DB"
database_name = "..."
database_id = "..."
```

Bindings declared, IDs in config, secrets via CLI.

## Secrets

```bash
wrangler secret put API_TOKEN
# prompts for value; stored encrypted in Cloudflare
```

Use `env.SECRET_NAME` in code. NEVER in `wrangler.toml`, NEVER in git.

## KV (eventually consistent)

```ts
await env.KV.put("user:123", JSON.stringify(user), { expirationTtl: 3600 })
const user = JSON.parse(await env.KV.get("user:123"))
```

Updates are eventually consistent (60s globally). Strong consistency → D1.

## D1 (SQLite at edge)

```ts
const user = await env.DB.prepare("SELECT * FROM users WHERE id = ?").bind("123").first()
await env.DB.prepare("INSERT INTO users (id, name) VALUES (?, ?)").bind("123", "Alice").run()
```

SQLite semantics. Transactions via `db.batch([...])`.

## R2 (object storage)

```ts
await env.BUCKET.put("file.pdf", data, { httpMetadata: { contentType: "application/pdf" } })
```

S3-like API. No egress fees. Public buckets for static.

## Local Dev

```bash
wrangler dev
# local server with bindings simulated
```

`--remote` for actual Cloudflare bindings. `--local` for fast iteration.

## Common Mistakes

Node.js APIs (`fs`, `Buffer`, `child_process`); large bundles; secrets in toml; HTTP to own service; missing `compatibility_date`; KV for transactional data (use D1); D1 for hot cache (use KV); no `wrangler dev`.

## Red Flags

`import fs` / `Buffer`; bundle > 1MB; secrets in toml; `fetch('https://my-db.example.com')`; D1 for cache; KV for transactions.

## Anti-Patterns

**Node.js APIs**; **secrets in toml**; **HTTP to own service**; **huge bundle**; **D1 for cache**; **KV for transactions**; **missing `compatibility_date`**.

## Verification

`wrangler dev` runs locally with simulated bindings; bundle stays small (red flag > 1MB); `compatibility_date` set; secrets absent from `wrangler.toml` and git; no Node.js APIs (`fs`, `Buffer`, `child_process`) imported.

## Skill Result Contract

```
<skill_result>
  <skill>cloudflare</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>`wrangler dev` runs with simulated bindings; bundle small; compatibility_date set</evidence>
  <artifacts>Worker code, wrangler.toml bindings, secrets via CLI</artifacts>
  <risks>Node.js APIs, secrets in toml, huge bundle, or none</risks>
</skill_result>
```

## References

N/A, no reference files; this skill is self-contained.
