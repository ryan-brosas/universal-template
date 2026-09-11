<!-- capsule-v2 -->
# TrackingId 16-byte identity twins — how do I mint LinkedIn's per-action `trackingId` for mutation payloads, and why do a raw charString and a base64 twin both exist?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory project `open-linkedin-api`. **Question:** what exact byte-level procedure generates a valid `trackingId` for voyager mutations (connect/message), and which encoding does each endpoint family expect — and is it actually random or derived from the target?

## 16 random bytes → chr-join charString OR base64 slice

**Path/Symbol:** `open_linkedin_api/utils/helpers.py:generate_trackingId_as_charString` (:247–255) + `generate_trackingId` (:258–266); consumers in `linkedin.py` (`add_connection` payload `"trackingId": generate_trackingId_as_charString()` :1290–1293; message-send payload uses `generate_trackingId_as_charString()` via `_post` body at the send-message site).
**Signature:** `generate_trackingId_as_charString() -> str`; `generate_trackingId() -> str`.
**Data Shape:** 16 random bytes (one `random.randrange(256)` per position); charString twin = `"".join(chr(i) for i in bytes)` (16 chars, code points 0–255, NOT text — it must ride an ISO-8859-1-safe transport layer); base64 twin = `str(base64.b64encode(bytes))[2:-1]` (24-char `b'...'` repr stripped to raw b64).

### Decisive source
```python
def generate_trackingId_as_charString():
    random_int_array = [random.randrange(256) for _ in range(16)]
    rand_byte_array = bytearray(random_int_array)
    return "".join([chr(i) for i in rand_byte_array])     # RAW BYTES as str

def generate_trackingId():
    random_int_array = [random.randrange(256) for _ in range(16)]
    rand_byte_array = bytearray(random_int_array)
    return str(base64.b64encode(rand_byte_array))[2:-1]   # printable b64 form
```

**Flow:** caller mints ONE fresh trackingId per mutation → embeds it verbatim in the JSON/REST payload field `trackingId` (e.g. `add_connection` posts `{trackingId, emberEntityName: 'growth/invitation/norm-invitation', invitee…}`) → server echoes it on the created object so clients can correlate the response row with the request.
**Invariant:** this id is CLIENT-MINTED CORRELATION NOISE, not a security token and not derived from the target profile — the target is addressed by the SEPARATE `profileId`/`toMember` field (contrast private-api's sendInvitation where `trackingId` comes from the SEARCH HIT because that API surface reuses server-issued ids). The two encodings are byte-identical twins: endpoints whose payloads pass through binary-tolerant layers take the charString; text-only contexts take base64. Picking the wrong twin for an endpoint yields silent 999s/rejections, not schema errors. Fresh randomness per call is required — reusing one value across invites makes bulk actions trivially correlatable.
**Probe:** no upstream tests in-repo — coverage caveat recorded (consistent with every other open-linkedin-api capsule). Deterministic probes verified at HEAD (anchored at the `open_linkedin_api/` package dir): `grep -c "randrange(256)" utils/helpers.py` ⇒ 2 (both twins share the same byte-array construction); `grep -n "trackingId" linkedin.py | head -3` ⇒ import :22–23 + single decisive consumer :1292; graph anchor resolves: search_graph project `open-linkedin-api` query `generate_trackingId`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "generate_trackingId", limit: 5 });
```

## Verdict
Adopt the shape: 16 fresh random bytes, client-minted per action, echoed by the server for correlation; keep both encodings in your port and match them to endpoint families empirically (charString first, base64 when the transport mangles non-text). Adapt entropy source to your runtime (`crypto.randomBytes(16)` / `secrets.token_bytes`). Omit nothing structural. Contrast: send-then-verify-invitation documents the private-api twin where trackingId is SERVER-ISSUED from search hits; voyager-mutation-endpoints shows the EasyApplyJobsBot variant embedding the same charString twin in its message-send body. Coverage caveat: source-grounded only; endpoint acceptance may rotate against live LinkedIn.
