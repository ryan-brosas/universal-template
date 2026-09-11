<!-- capsule-v2 -->
# Plan-gated chat rate limits — how does a per-minute send limit follow the workspace's plan, and what should a 429 tell the client?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When usage limits are a product tier rather than an abuse guard, where do the numbers live, what is the limiter keyed by, and how does the rejection response stay machine-actionable?

## Plan-enum limits + team-keyed limiter + structured 429
**Path/Symbol:** `app/Enums/Plan.php` (`rateLimit`, 71L whole; `credits`/`rank` siblings); `app/Providers/AppServiceProvider.php:351-366` (`RateLimiter::for('chat-send', ...)`).
**Signature:** `Plan::rateLimit(): int` — match: Free 10 / Pro 30 / Enterprise 60. Limiter: `Limit::perMinute($team->plan->rateLimit())->by($team->getKey())->response(fn (Request $request, array $headers) => ... 429 JSON)`.
**Data Shape:** 429 body: `{error: 'rate_limited', message: <human copy>, retry_after_seconds: <int from Retry-After header>, plan: <plan value>}`; headers forwarded from the limiter. Anonymous senders share one `chat-anon` key at `Plan::default()->rateLimit()`.

### Decisive source
```php
return Limit::perMinute($team->plan->rateLimit())
    ->by($team->getKey())
    ->response(function (Request $request, array $headers) use ($team) {
        ChatTelemetry::rateLimited(teamId: (string) $team->getKey(), plan: $team->plan->value);
        $seconds = (int) ($headers['Retry-After'] ?? 0);
        return response()->json([
            'error' => 'rate_limited',
            'message' => "You're sending messages quickly. You can send again in {$seconds} seconds.",
            'retry_after_seconds' => $seconds,
            'plan' => $team->plan->value,
        ], 429, $headers);
    });
```

**Flow:** every chat-send request resolves the user's currentTeam → the limit VALUE comes from the plan enum (single source of truth; the same enum also carries credit allowances and plan rank) → the limiter is keyed by TEAM id, so all members of a workspace share one bucket (a per-user key would let a five-seat team send 5× the plan's rate) → on rejection the custom response emits a telemetry breadcrumb AND a structured JSON body whose `retry_after_seconds` is parsed back out of the limiter's own Retry-After header. Sibling limiters: `mcp` 120/min per user-or-IP, `mcp-oauth` 20/min per IP (pre-auth consent endpoints), token endpoints 300 read / 60 write per key split by HTTP method.
**Invariant:** The limit number lives in the plan enum, never inline in the limiter — adding a tier must not require touching rate-limit code. The bucket key is the workspace, not the user. The 429 must carry a machine-readable wait time; a bare status code forces clients to guess or hammer.
**Probe:** `tests/Feature/Chat/ChatRateLimitTest.php` + `tests/Feature/Chat/ChatSendRateLimitTest.php` — plan-dependent send limiting and the structured 429 contract.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "RateLimiter chat-send rateLimit Limit perMinute retry_after_seconds ChatTelemetry rateLimited", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt plan-tier limits as enum methods consumed by named limiters, team-keyed buckets for shared workspaces, and a structured 429 that echoes Retry-After as a body field plus telemetry. Adapt the Laravel RateLimiter facade and the chat-anon anonymous bucket to your framework's limiter surface.
