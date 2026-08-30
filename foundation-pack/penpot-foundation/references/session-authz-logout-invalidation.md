<!-- capsule-v2 -->
# Session authz + logout invalidation — how does cookie/bearer auth resolve a session, renew it, and how must logout actually kill it?

**Source:** penpot MPL-2.0 `develop@64a52d6b` (7c85837 "Fix session invalidation on logout to prevent token replay", GHSA-mj9f-5cwq-7p3q); Codebase Memory project `mnt-hdd-utopia-inspo-external-penpot`. **Question:** What does a correct session lifecycle look like when the token is stateless but the session is a DB row?

## wrap-authz dual-token resolution + delete-fn fix
**Path/Symbol:** `backend/src/app/http/session.clj` (`default-renewal-max-age` :37 = 6h; `assign-token` :166-181; `delete-fn` :203-208; `get-session` :211-213; `renew-session?` :251-256; `wrap-authz` :258-302; `assign-session-cookie` :309-330) + direct tests `backend/test/backend_tests/rpc_auth_test.clj` (4 deftests).
**Signature:** `(delete-fn cfg) -> (fn [request response] -> response')`; `wrap-authz handler cfg -> handler'`.
**Data Shape:** token claims `{... :sid session-id}` with `metadata {:ver 0|1}`; ver 0 = OLD self-contained tokens (`read-session manager token`), ver 1 = DB-backed via sid. Request carries `::session` map after authz.

### Decisive source
```clojure
;; THE FIX (was: (some->> (get request ::id) ...) — deleted by request-scoped
;; id that was never populated, so server-side row survived logout):
(defn delete-fn [{:keys [::manager]}]
  (fn [request response]
    (some->> (get request ::session) :id (delete-session manager))
    (clear-session-cookie response)))

(defn- renew-session?
  [{:keys [id modified-at] :as session}]
  (or (string? id)
      (and (ct/inst? modified-at)
           (neg? (compare default-renewal-max-age elapsed)))))
```

**Flow:** wrap-authz branches on auth type — `:cookie` reads session per token version (ver 0 legacy read-by-token, ver 1 `some->> (:sid claims)`), attaches `::profile-id` + `::session` to the request, and if `(renew-session? session)` re-writes the row, mints a fresh token, and REPLACES the response's session cookie; `:bearer` resolves identically but NEVER renews (API clients can't store cookies). Logout is implemented as a response TRANSFORM (`rph/with-transform` in auth/logout calls delete-fn): it now deletes the DB ROW keyed off the resolved session, then clears the cookie (`{:value "" :max-age 0}`). Renewal window: sessions younger than 6h get refreshed on activity.
**Invariant:** Token replay protection = server-side deletion, not cookie clearing alone — a stolen post-logout token must fail because `read-session` on the deleted sid returns nil (test `replay-after-logout-cannot-authenticate`). Logout of one session never touches sibling sessions of the same profile (SQL uses `id != ?` only in invalidate-others; plain row-delete in delete-fn); cookie clearing is IDEMPOTENT even when no session existed (`logout-clears-cookie-even-when-session-missing`).
**Probe:** direct tests `backend/test/backend_tests/rpc_auth_test.clj`: `logout-invalidates-current-session` (:22-46) inserts a real `http_session_v2` row, runs delete-fn, asserts `read-session` nil + cookie cleared; `logout-does-not-invalidate-other-sessions` (:70-95); `replay-after-logout-cannot-authenticate` (:97-112). Grep anchor from repo root: `grep -c 'delete-session manager' backend/src/app/http/session.clj` → 3.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-external-penpot","query":"delete-fn wrap-authz renew-session session","limit":5,"detail":"ids"}'
```
(rank 1-3: `wrap-authz` 258-302, `renew-session?` 251-256, `delete-fn` 203-208.)

## Verdict
Adopt the versioned-token resolution ladder, renewal-window-on-cookie-only rule, and resolve-then-delete-row logout with idempotent cookie clear. Adapt storage (`http_session_v2`) and JWT claims to your stack. Omit Penpot's SSO props plumbing (`clear-organization-sso-sessions!` jsonb path removal) unless you run multi-org SSO.
