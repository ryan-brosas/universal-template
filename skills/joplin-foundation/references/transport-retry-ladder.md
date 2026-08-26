<!-- capsule-v2 -->
# Transport retry ladder — when may a failed storage request be repeated, who opts into retrying, and why doesn't the fetch layer double-retry?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How do you bound-retry flaky transport calls without ever retrying errors where repetition changes semantics or cannot help?

## tryAndRepeat: opt-in count + error-code gate + suppressed inner fetch retries
**Path/Symbol:** `packages/lib/file-api.ts:101-125` (`tryAndRepeat`), :79-99 (`requestCanBeRepeated`), :280-284 (`requestRepeatCount`); applied in `put` :401-409 and `delta` :441-444.
**Signature:** `tryAndRepeat<T>(fn, count): Promise<T>`; `requestCanBeRepeated(error: {code?}): boolean`; `driver.requestRepeatCount?(): number`.
**Data Shape:** repeatable budget resolved as FileApi-instance override → optional driver override → default 0 (= never retry); backoff sleeps `1 + retryCount * 3` seconds, linearly.

### Decisive source
```ts
async function tryAndRepeat<T>(fn, count) {
    // Don't use internal fetch retry mechanim since we are already retrying here.
    const shimFetchMaxRetryPrevious = shim.fetchMaxRetrySet(0);
    const defer = () => { shim.fetchMaxRetrySet(shimFetchMaxRetryPrevious); };
    while (true) {
        try { const result = await fn(); defer(); return result; }
        catch (error) {
            if (retryCount >= count || !requestCanBeRepeated(error)) { defer(); throw error; }
            retryCount++;
            await time.sleep(1 + retryCount * 3);
        }
    }
}
function requestCanBeRepeated(error) {
    const errorCode = typeof error === 'object' && error.code ? error.code : null;
    if (errorCode === 403 || errorCode === 401) return false;      // auth/permission won't heal
    if (errorCode === 'rejectedByTarget' || errorCode === 'isReadOnly') return false;  // target said no
    if (errorCode === 'methodNotSupported') return false;          // route unsupported
    if (errorCode === 'failSafe') return false;                    // server-side issue; keep logs quiet
    return true;
}
public requestRepeatCount() {
    if (this.requestRepeatCount_ !== null) return this.requestRepeatCount_;
    if (this.driver_.requestRepeatCount) return this.driver_.requestRepeatCount();
    return 0;
}
```

**Flow:** every transport call goes `FileApi.put/delta/… → tryAndRepeat(driverCall, requestRepeatCount())`; WebDAV overrides `requestRepeatCount()` to hardcode 3 (flaky servers), Amazon S3/Dropbox/JoplinServer override too, while local/memory/OneDrive inherit 0 (never repeat); on failure the error CODE decides — auth failures, explicit target rejections, unsupported methods and failSafe aborts throw immediately, anything else backs off linearly (4s, 7s, 10s…) until the budget is spent.
**Invariants:** (1) repetition is OPT-IN per driver — default zero means a new backend gets no surprise retry storms; (2) the five non-repeatable codes are semantic verdicts, not transient faults — repeating them wastes quota or duplicates side effects (failSafe also keeps log noise down since FileApi prints lastRequests there); (3) inner fetch-level retries are forced to 0 for the duration and restored in `defer()` on BOTH success and final failure — exactly one retry layer owns the backoff; (4) budget check precedes the sleep, so the last attempt adds no delay.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "await time.sleep(1 + retryCount * 3);" packages/lib/file-api.ts && grep -cF "if (errorCode === '"'"'failSafe'"'"') return false;" packages/lib/file-api.ts && grep -cF "return tryAndRepeat(() => this.driver_.delta(this.fullPath(path), options), this.requestRepeatCount());" packages/lib/file-api.ts && grep -cF "requestRepeatCount() {" packages/lib/file-api-driver-webdav.js'` (anchored at repo root; expects 1 / 1 / 1 / 1). Coverage caveat: NO direct unit test exercises tryAndRepeat/requestRepeatCount at this pin (grep over packages/lib *.test.ts finds no reference) — claims are source-pinned only.
**Layering note:** distinct from the Synchronizer-level error taxonomy capsule — that classifies failures AFTER the transport gives up; this owns whether the transport tries again first.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "tryAndRepeat requestCanBeRepeated requestRepeatCount fetchMaxRetrySet", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: opt-in bounded retry with linear backoff gated by an explicit non-retryable code ladder, single-owner suppression of nested retry layers. Adapt: the code list to your storage's error vocabulary. Omit: shim fetch plumbing specifics.
