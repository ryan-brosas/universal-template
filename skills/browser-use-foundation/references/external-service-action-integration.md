<!-- capsule-v2 -->
# External-service action integration — how do you expose an OAuth'd third-party API (Gmail) as a fail-soft agent action?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you register an external service's capabilities into an agent action registry so auth problems inform the LLM instead of crashing the step, and bulky payloads enter memory exactly once?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/integrations/gmail/service.py` — `GmailService.authenticate` (:77-137), `get_recent_emails` (:139-190); `browser_use/integrations/gmail/actions.py` whole (115L) — `register_gmail_actions` (:29-115), `GetRecentEmailsParams` (:22-26).
**Signature:** `async authenticate() -> bool`; `async get_recent_emails(max_results=10, query='', time_filter='1h') -> list[dict]`; `register_gmail_actions(tools: Tools, gmail_service=None, access_token=None) -> Tools`.
**Data Shape:** service layer returns primitives (`bool` / `list`) and NEVER raises; the action layer converts outcomes into `ActionResult(extracted_content, long_term_memory, error)`.

### Decisive source
```python
# service.authenticate — token ladder, every failure path returns False
if self.access_token:
    self.creds = Credentials(token=self.access_token, scopes=self.SCOPES)   # 1. direct token
elif os.path.exists(self.token_file):
    self.creds = Credentials.from_authorized_user_file(...)                 # 2. cached json
if not self.creds or not self.creds.valid:
    if self.creds and self.creds.expired and self.creds.refresh_token:
        self.creds.refresh(Request())                                       # 3. refresh
    else:
        if not os.path.exists(self.credentials_file): return False          # loud log + False
        self.creds = InstalledAppFlow.from_client_secrets_file(...).run_local_server(port=8080)  # 4. OAuth
    await anyio.Path(self.token_file).write_text(self.creds.to_json())      # persist for next run
except Exception:
    return False

# service.get_recent_emails — fail-soft list contract
if not self.is_authenticated(): return []
if time_filter and 'newer_than:' not in query:
    query = f'newer_than:{time_filter} {query}'.strip()   # inject ONLY if absent
except HttpError: return [] ; except Exception: return []

# actions.py — module-global singleton + lazy auth INSIDE the action
_gmail_service: GmailService | None = None
if not _gmail_service.is_authenticated():
    authenticated = await _gmail_service.authenticate()
    if not authenticated:
        return ActionResult(extracted_content='Failed to authenticate with Gmail. ...',
                            long_term_memory='Gmail authentication failed')   # informative, NOT error=
return ActionResult(
    extracted_content=full_email_dump,
    include_extracted_content_only_once=True,   # big payload into memory ONCE
    long_term_memory=f'Retrieved {len(emails)} recent emails ...')             # compact summary forever
```
**Flow:** registration binds one module-global service (pre-built > access-token > default) and closes over it in a decorated action → on call the action lazily authenticates → auth failure returns an instructive `extracted_content` (the LLM can react; the step does not fail) → success returns full email text with `include_extracted_content_only_once=True` so the dump is shown once but only the compact summary persists to long-term memory → any exception sets `error=` + short memory.
**Invariant:** the two-channel split of agent feedback — `extracted_content` is what the model sees this turn, `long_term_memory` is what persists across turns; oversized payloads must pair `include_extracted_content_only_once=True` with a summarized `long_term_memory`. Auth failure ≠ action error: only genuine exceptions set `error=`. The service/action layering keeps ALL vendor exceptions inside the service (bool/list contracts), so the registry never sees them. The `'newer_than:' not in query` guard makes time-filter injection idempotent even though the action also hardcodes its own filter.
**Probe:** no dedicated upstream unit test (documented caveat). Executed probe (repo .venv) through the REAL registry: `GetRecentEmailsParams().max_results == 3`, `max_results=51` rejected by pydantic bounds (ge=1 le=50); `register_gmail_actions(tools) is tools`; `execute_action('get_recent_emails', {'keyword': 'github', 'max_results': 3})` with uninitialized singleton → `ActionResult(error='Error getting recent emails: Gmail service not initialized', long_term_memory='Failed to get recent emails due to error')`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "GmailService authenticate get_recent_emails register_gmail_actions token_file InstalledAppFlow run_local_server", limit: 8, fields: ["lines"] });
```
Top hits: `get_recent_emails` :139-190, `authenticate` :77-137, `register_gmail_actions` :29-115; nearest neighbors are the cloud-sync device-auth twins (`DeviceAuthClient.authenticate` :275-343) showing the same fail-soft auth shape in another plane.

## Verdict
Adopt the service/action layering for ANY external OAuth service behind an agent tool: primitive-returning fail-soft service, singleton bound at registration, lazy in-action authentication, instructive extracted_content on auth trouble, and once-only inclusion for large payloads with a compact persistent summary. Adapt scopes, token-file location, and the local-server redirect port to your vendor. Omit Google-specific parsing (`_parse_email`) and the hardcoded 5-minute window.
