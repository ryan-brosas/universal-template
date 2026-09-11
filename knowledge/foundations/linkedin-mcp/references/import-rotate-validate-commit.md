<!-- capsule-v2 -->
# Import rotate-validate-commit — how do you adopt a foreign credential without destroying the working session it replaces?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** What is the safe order for retiring, validating and committing a replacement session under concurrency?

## Three-tier selection → lease → rotate → validate-per-candidate → restore-on-failure
**Path/Symbol:** `linkedin_mcp_server/browser_import/orchestrate.py:import_session_from_browser` (:193), `rank_live_profiles` (:74), `_extract_and_stage` (:149), `_import_holding_the_profile` (:272), `_import_first_accepted` (:325); drivers validation `validate_imported_cookies` (`drivers/browser.py`:324).
**Signature:** `async def import_session_from_browser(browser: str | None, *, user_data_dir: Path, superseded_by=UNGUARDED) -> bool`; blocking helpers kept sync for one-hop `asyncio.to_thread` offload.
**Data Shape:** Candidate = `(BrowserProfile, LiAtMeta)`; live = non-app-bound AND (`expires == -1.0` session cookie OR future expiry); ranked by `li_at.last_access` DESC (most recently used browser first). Staged payload = full LinkedIn cookie superset at 0o600.

### Decisive source
```text
Three-tier selection, cheapest first — keychain is touched ONLY for the browser
actually imported: (1) plaintext SQLite pre-filter (no decryption, no prompt)
drops logged-out/expired; (2) recency ranking, still keychain-free; (3)
authoritative confirm per candidate: decrypt (keychain prompt) → inject →
prove /feed/. First pass wins; server-rejected falls through to next-freshest.

Ordering rules that cost measurements:
- close_browser() BEFORE staging: a later teardown must not export the RETIRED
  session's cookies over the freshly staged ones.
- lease.try_acquire() BEFORE rotate: validation launches Chromium on the source
  profile; without the lease another process could launch the moment staged
  cookies land.
- peer check WITH the profile in hand (superseded_by guard): two clients meeting
  one bad session both decide to repair; the loser rotated away the session the
  winner had just imported. Measured with two real processes.
- rotate_shielded BEFORE mark_browser_open(): the exclusivity check treats an
  open browser as refuse-reason, so marking first would block every re-import
  from retiring what it replaces.
- Failure bookkeeping: BrowserShutdownUnconfirmedError ⇒ release_profile=False
  (validation Chromium may still hold the profile); finally-block restores the
  retired quarantine copy when nothing was imported — via run_deferring_cancels,
  re-raising CancelledError after the move completes so a cancel can't split a
  session across quarantine and live paths.
- Undecryptable-but-present raises CookieDecryptionError ("fix keychain access")
  DISTINCT from decrypted-but-rejected False ("sign in again") — different user
  remediations must not share an error shape.

Why rotation at all: Chromium keeps machine_id and friends for the LIFE of a
profile directory; importing a possibly-different account into the old dir would
present two accounts to LinkedIn as one device.
```

**Flow:** discover+rank off-loop → close singleton → acquire profile lease → peer-session short-circuit → rotate (quarantine timestamped backup) → per candidate: stage cookies → headless validation browser proves /feed/ (local BrowserManager, never the export-on-close singleton, so `cookies.json` cannot shrink) → first accept writes source-state and commits; all-rejected restores the retired session.
**Invariant:** The working session survives every failure mode: rotation happens before validation, restoration happens whenever no replacement committed, and an unconfirmed shutdown keeps BOTH the lease and the quarantine instead of guessing.
**Probe:** `grep -c 'rotate_shielded(user_data_dir)' linkedin_mcp_server/browser_import/orchestrate.py` → 1; `grep -c 'last_access, reverse=True' linkedin_mcp_server/browser_import/orchestrate.py` → 1; direct tests: `tests/test_browser_import_orchestrate.py::test_rank_orders_by_last_access_desc` (:106), `test_import_tries_next_browser_when_first_rejected` (:194), `test_import_live_but_undecryptable_raises_decryption_error` (:353).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "import_session_from_browser rank_live_profiles rotate_shielded", limit: 5 });
```

## Verdict
Adopt cheapest-first credential triage plus rotate-validate-commit-with-restore for any session adoption flow. Adapt discovery paths/keystore APIs to your OS matrix. Omit Chromium cookie encryption internals (see extract.py).
