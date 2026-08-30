<!-- capsule-v2 -->
# Voyager mutation endpoints — how do I POST to LinkedIn's Voyager API for state-changing actions (connect, message, follow, react, reply) and read the error-state return convention?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c` (`linkedin.py` 1787L). Codebase Memory `open-linkedin-api`. **Question:** what is the POST-vs-GET discipline and the boolean error-state return convention that every mutation shares, and what payload shapes do the four action families use?

## Mutation POST family
**Path/Symbol:** `linkedin.py:Linkedin.add_connection` (:1412–1461), `send_message` (:1256–1316), `reply_invitation` (:1379–1410), `follow_company` (:1186–1203), `react_to_post` (:1744–1763), `remove_connection` (:1463–1477), `mark_conversation_as_seen` (:1318–1333). Transport `_post` (:99–104) vs `_fetch` (:84–89). **Signature:** every mutation returns `bool` = **error state** (True = error, False = success); GETs return parsed data.
**Data Shape:** mutations POST to `/voyager...` endpoints with `action`/`decorationId` params and a JSON payload; success is judged per-endpoint (201 for message/reaction, 200 for follow/seen/reply, `res.ok` for add_connection).

### Decisive source
```python
def _post(self, uri, evade=default_evade, base_request=False, **kwargs):
    evade()                                  # every request flows through the pacing transport
    url = f"{self.client.API_BASE_URL if not base_request else self.client.LINKEDIN_BASE_URL}{uri}"
    return self.client.session.post(url, **kwargs)

# add_connection: action + decorationId params, invitee union payload
payload = {"invitee": {"inviteeUnion": {"memberProfile": f"urn:li:fsd_profile:{profile_urn}"}},
           "customMessage": message}
params = {"action": "verifyQuotaAndCreateV2",
          "decorationId": "com.linkedin.voyager.dash.deco.relationships.InvitationCreationResultWithInvitee-2"}
res = self._post("/voyagerRelationshipsDashMemberRelationships", data=json.dumps(payload),
                 headers={"accept": "application/vnd.linkedin.normalized+json+2.1"}, params=params)
return res.ok == False          # True = error (e.g. CANT_RESEND_YET pending connection)

# send_message: originToken uuid + trackingId char-string, dedupe flag
message_event = {"eventCreate": {"originToken": str(uuid.uuid4()),
    "value": {"com.linkedin.voyager.messaging.create.MessageCreate": {
        "attributedBody": {"text": message_body, "attributes": []}, "attachments": []}},
    "trackingId": generate_trackingId_as_charString()},
    "dedupeByClientGeneratedToken": False}
# react_to_post: threadUrn param + reactionType body
params = {"threadUrn": f"urn:li:activity:{post_urn_id}"}
payload = {"reactionType": reaction_type}
```

**Flow:** every mutation calls `_post` (which runs `evade()` pacing first) → builds a JSON payload + `action`/`decorationId`/`threadUrn` params → POSTs to the Voyager endpoint with the `application/vnd.linkedin.normalized+json+2.1` accept header → returns `status_code != <expected>` as the error-state bool.
**Invariant:** the boolean return is INVERTED from intuition — `True` means an error occurred, `False` means success — so callers check `if add_connection(...)` to detect failure. GET reads (`_fetch`) and POST writes (`_post`) are strictly separated; a mutation never goes through `_fetch`. Message dedupe is the caller's job (`dedupeByClientGeneratedToken: False` + client-generated `originToken`/`trackingId`). add_connection validates message length (≤300) and resolves `fs_miniProfile` → `fsd_profile` URN namespacing before POSTing.
**Probe:** no upstream tests — coverage caveat recorded. Graph anchors resolve: `add_connection`, `send_message`, `reply_invitation`, `react_to_post`, `follow_company`, `_post`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "add_connection", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "send_message", limit: 5 });
```

## Verdict
Adopt the strict GET/POST split, the inverted error-state bool convention, and the `action`+`decorationId`+normalized-JSON-header mutation shape; adapt endpoint paths and payload field names (rotate); omit the hard-coded decorationId strings (they rotate against live LinkedIn). Caveat: source-grounded only, no test coverage.
