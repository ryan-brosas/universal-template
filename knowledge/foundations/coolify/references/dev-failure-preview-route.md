<!-- capsule-v2 -->
# Dev-only failure preview route: env-gated fault injection behind an allowlisted abort

## Source
Coolify `main@98116397`: `app/Livewire/Dev/LivewireRequestFailurePreview.php` (31L whole file), route registration `routes/web.php` (:121-127 inside `app()->environment(['local','testing'])` block), view `resources/views/livewire/dev/livewire-request-failure-preview.blade.php` (23L). Drift-introduced plane (upstream commit `c1219576`); direct tests `tests/Feature/LivewireRequestFailurePreviewTest.php` + `tests/v4/Browser/LivewireRequestFailurePreviewTest.php` (Dusk).

## Question
How do you ship a fault-injection endpoint for testing failure UX without ever exposing it in production?

## Path / Symbol
`LivewireRequestFailurePreview::fail(int $status): never`; route `GET /__livewire-request-failure` named `dev.livewire-request-failure-preview`, registered ONLY under `local|testing`.

## Signature
```php
/** @var list<int> */
public array $statuses = [502,503,504,520,521,522,523,524,525,526,527,530];

public function fail(int $status): never {
    abort_unless(in_array($status, $this->statuses, true), Response::HTTP_NOT_FOUND);
    throw new HttpResponseException(response(
        '<!doctype html><html><body><h1>Gateway time-out</h1><p>cloudflare proxy error '.$status.'</p></body></html>',
        $status,
        ['Content-Type' => 'text/html']
    ));
}
```

## Data Shape
Allowlist mirrors `INFRASTRUCTURE_FAILURE_STATUSES` in resources/js/livewire-request-failure.js exactly (12 codes) — the preview exists solely to exercise the toast handler; body mimics a Cloudflare HTML error page because real gateway failures return HTML, not Livewire JSON.

## Decisive source
Three-layer containment:
1. Route-level: registered inside `if (app()->environment(['local', 'testing']))` — production never mounts it (same pattern as sibling `/__exception`).
2. Parameter-level: strict `in_array(..., true)` allowlist → any other status 404s, so the endpoint can't be turned into an arbitrary-status reflector even locally.
3. Payload-level: static HTML with the injected status code only — no user data echoed back.

## Flow / Invariant
INVARIANTS:
- `fail()` throws `HttpResponseException` (never-type) instead of returning a response — required so Livewire's request pipeline treats it as a mid-request abort, reproducing the real interruption shape the JS handler sees.
- Status set duplication across PHP + JS is DELIBERATE (two sides of one test scenario); keep them mirrored or drive both from one source when porting.
- The Dusk test drives the browser flow end-to-end (gesture → failing request → toast), pairing this route with livewire-request-failure.js as behavior spec.

## Probe (direct tests)
From repo root:
```bash
grep -c "'/__livewire-request-failure'" routes/web.php
grep -c 'abort_unless(in_array($status, $this->statuses, true)' app/Livewire/Dev/LivewireRequestFailurePreview.php
sed -n '/__livewire-request-failure/{=;p}' routes/web.php | head -4
```
Expect 1 / 1 / line numbers falling inside the local/testing env block. (PHPUnit runner blocked honestly.)

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"LivewireRequestFailurePreview fail status","limit":3}'
```
→ rank-1 `Method app/Livewire/Dev/LivewireRequestFailurePreview.php 16-25`.

## Verdict
ADAPT — the env-gate + allowlist-abort + realistic-error-body triad ports to any app needing reproducible gateway-failure UX tests.
