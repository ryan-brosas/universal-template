<!-- capsule-v2 -->
# HMAC session token codec (Go) — how do you mint stateless, expiring, self-contained session tokens without JWT overhead?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the exact wire format of the ingest token, and how does the server distinguish "expired" from "expired 30 seconds ago" (and why does that matter)?

## Tokenizer Compose / Parse / TokenData
**Path/Symbol:** `backend/pkg/token/tokenizer.go:Compose` (:39-45), `Parse` (:47-79), `sign` (:33-37), `TokenData` (:27-31), sentinels `EXPIRED`/`JUST_EXPIRED` (:14-17).
**Signature:** `func (tokenizer *Tokenizer) Compose(d TokenData) string`; `func (tokenizer *Tokenizer) Parse(token string) (*TokenData, error)`; `TokenData{ID uint64; Delay int64; ExpTime int64}`.
**Data Shape:** Token = `<base36(ID)>.<base36(Delay)>.<base36(ExpTime)>.<base58(HMAC-SHA256(body))>` — four dot-separated fields; secret is a shared static key (`NewTokenizer(secret)`).

### Decisive source
```go
func (tokenizer *Tokenizer) Parse(token string) (*TokenData, error) {
	data := strings.Split(token, ".")
	if len(data) != 4 { return nil, errors.New("wrong token format") }
	if !hmac.Equal(                                  // constant-time compare
		base58.Decode(data[len(data)-1]),
		tokenizer.sign(strings.Join(data[:len(data)-1], ".")),
	) { return nil, errors.New("wrong token sign") }
	...parse id/delay/expTime from base36...
	if expTime <= time.Now().UnixMilli() {
		if expTime+30000 > time.Now().UnixMilli() {
			return res, JUST_EXPIRED                // grace window
		}
		return res, EXPIRED
	}
	return res, nil
}
```

**Flow:** start-session mints `{ID: flakeID(startTimeMili), Delay: serverMs - clientTs, ExpTime: start + MaxSessionDuration}` and Composes → tracker echoes the token on every beacon → push handler `Parse`s it per request (stateless auth, no session lookup needed for authn) → JUST_EXPIRED lets the CURRENT batch through but flags a 401-after-write response so the client restarts its session WITHOUT losing the in-flight batch.
**Invariant:** The 30-second JUST_EXPIRED grace exists because batches are encoded BEFORE the fetch: rejecting a batch whose token expired mid-encode would drop up to ~30 s of user interaction every MaxSessionDuration boundary. `hmac.Equal` (not `==`) keeps signature verification constant-time. Delay rides INSIDE the signed body so clients can't tamper with the server-clock offset used for timestamp normalization. Note the asymmetry with admin-plane auth: api/chalicelib uses real JWTs (audience-checked); this custom codec exists only on the high-QPS ingest path where JWT parse cost matters.
**Probe:** `grep -n 'JUST_EXPIRED' backend/pkg/token/tokenizer.go | head -3` from repo root → lines 16 and 74; `grep -c 'base58' backend/pkg/token/tokenizer.go` → **3** (verified live). Coverage caveat: `go test ./pkg/token/...` reports "no test files" at pin — behavior pinned by source anchors + the Go compile check, no direct unit test exists.
**Retrieve:** search_graph project openreplay query "Tokenizer Compose Parse TokenData" → rank-1 Methods `pkg.token.Parse :47-79`, `TokenData :27-31`, `Compose :39-45` line-exact.

## Verdict
Adopt base36-body + base58-HMAC-SHA256 stateless token with signed clock-offset and short grace-window expiry classification as pure authz behavior; adapt field set/encoding to your needs (JWT fine if QPS allows); omit the flake-ID composition if your IDs come from elsewhere.
