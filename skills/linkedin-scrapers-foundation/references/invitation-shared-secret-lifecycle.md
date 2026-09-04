
`<!-- capsule-v2 -->`
# Invitation shared-secret lifecycle — how do I list and ANSWER connection invitations when acceptance requires a server-minted secret the listing itself supplies?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** what exact credentials does accepting an invitation need, and where do they come from?

## Invitation lifecycle
**Path/Symbol:** `linkedin.py:Linkedin.get_invitations` (:1350–1377), `Linkedin.reply_invitation` (:1379–1410).
**Signature:** `get_invitations(start=0, limit=3) -> list`; `reply_invitation(invitation_entity_urn: str, invitation_shared_secret: str, action="accept") -> bool` (True = success).
**Data Shape:** `/relationships/invitationViews` (`q=receivedInvitation`, `start`/`count`, `includeInsights=True`) returns VIEW-wrapper elements — each element carries the invitation nested under `element["invitation"]` plus insights; the reply POST body needs `{invitationId, invitationSharedSecret, isGenericInvitation: False}`.

### Decisive source
```python
if res.status_code != 200:
    return []
response_payload = res.json()
return [element["invitation"] for element in response_payload["elements"]]

# reply side:
invitation_id = get_id_from_urn(invitation_entity_urn)
params = {"action": action}                      # "accept" | "reject"
payload = json.dumps({"invitationId": invitation_id,
                      "invitationSharedSecret": invitation_shared_secret,
                      "isGenericInvitation": False})
res = self._post(f"/relationships/invitations/{invitation_id}", params=params, data=payload)
return res.status_code == 200
```

**Flow:** list invitations (offset paging; non-200 degrades to `[]`) → pick one → derive numeric invitationId from its entityUrn via `get_id_from_urn` → POST to `/relationships/invitations/{id}` with action as QUERY param and BOTH server-minted credentials in the body.
**Invariant:** `invitationSharedSecret` is minted server-side and ONLY obtainable from the listing payload — it must round-trip verbatim; invitationId is never carried directly but split out of the entityUrn. A caller cannot distinguish "no invitations" from "request failed" by return value alone (both yield `[]`). Success is judged `status_code == 200` (body ignored).
**Probe:** no upstream tests exist in-repo (runner block recorded). Deterministic byte-exact grep against checkout HEAD resolves :1377 (view unwrap) / :1399 (sharedSecret):
```bash
grep -n 'invitationSharedSecret|element["invitation"]' open_linkedin_api/linkedin.py
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "reply_invitation", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "get_invitations", limit: 5 });
```

## Verdict
Adopt the credential round-trip (list-first, answer-second with the server-minted secret) and the view-envelope unwrap; adapt endpoint paths and the accept/reject action vocabulary per generation; omit includeInsights if unused. Contrast: `voyager-mutation-endpoints` covers the generic POST shape; this capsule pins the INVITATION-specific two-call dependency. Caveat: source-grounded only — no upstream test coverage.
