---
title: cloudflare
summary: Use when deploying to or configuring ANY Cloudflare service, Workers, Pages, KV, D1, R2, AI, Tunnel, WAF. MUST load before writing Cloudflare Workers code, wrangler configs, or infrastructure-as-code for Cloudflare.
kind: playbook
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

### Native widget management and private output

Check installed `wrangler turnstile widget --help` before assuming dashboard-only
setup or requiring another API token. Current Wrangler OAuth may already include
`challenge-widgets.write`. List and reuse the exact hostname's widget first.
Native widget `create` and `get` output contains its secret, including in JSON mode:
capture it privately and disable Wrangler disk logging with
`WRANGLER_WRITE_LOGS=false` for those calls. Return only public metadata and receipt
flags, not the raw native response.

### File-based setup without exposing credentials

A request for project-local `.env` configuration is not a request to commit a
credential or expose it in browser code. Wrangler supports local `.env` files;
a competing `.dev.vars` takes precedence. Reuse that native loading behavior
rather than adding another dotenv system or insisting on dashboard-only setup.
A hosted Worker does not read the developer's local file at runtime.

For an authorized file-to-host sync, select only the intended, nonempty secret
fields and pass them to native `wrangler secret bulk` through stdin. Do not upload
a whole development file containing public settings or activation flags. Keep
those with their existing production configuration owner. Blank local values
should not silently mean deleting a hosted credential.

Secret updates can publish a new serving version. Confirm the account and existing
Worker before writing; inspect native secret-name and deployment readback afterward.
Do not confuse a registered secret with a working provider integration: values
cannot be read back, and disabled application gates may still be intentional.
Check the installed CLI contract and [local environment precedence](https://developers.cloudflare.com/workers/local-development/environment-variables/).

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

## Verify configured I/O in the actual runtime

Bun/Node provider fixtures plus an unconfigured Worker smoke test leave an
important gap: the native outbound request path never runs. Exercise a configured
handler in workerd with loopback provider fixtures, retaining native `fetch` and
its options. Do not replace away the runtime behavior being tested.

For example, the runtime shipped with Wrangler 4.145.0 rejected
`redirect: "error"` although Bun accepted it and Cloudflare's request docs listed
it. `manual` plus explicit non-2xx rejection preserved the intended no-forwarding
boundary. A failing native-runtime regression, then the live read, established
the fix; token authentication and a successful build did not.

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


## References

N/A, no reference files; this skill is self-contained.
