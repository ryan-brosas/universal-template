<!-- capsule-v2 -->
# Session-key in DB + signer — where does the signing secret live and what does it sign?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How is `session-key` generated/persisted, and which token shapes share the signer?

## Preferences + URLSafeTimedSerializer
**Path/Symbol:** `isso/db/preferences.py:Preferences` (7–29); wiring `isso/__init__.py:Isso.__init__` (101); consumers edit-cookie/moderate/unsubscribe/admin.
**Signature:** `signer = URLSafeTimedSerializer(self.db.preferences.get("session-key"))`; defaults row minted once via `binascii.b2a_hex(os.urandom(24))`.
**Data Shape:** preferences table `(key VARCHAR PRIMARY KEY, value VARCHAR)`; payload shapes seen by ONE serializer: `[id, sha1hex]`, `("unsubscribe", email)`, `id`, `{"logged": True}`, `comment["id"]`.

### Decisive source
```python
class Preferences:
    defaults = [
        ("session-key", binascii.b2a_hex(os.urandom(24)).decode("utf-8")),
    ]
    def __init__(self, db):
        ...
        for key, value in Preferences.defaults:
            if self.get(key) is None:
                self.set(key, value)
```

**Flow:** first boot writes a random 48-hex-char key; every later boot reuses it (restarts must NOT invalidate outstanding moderation links or 15-min edit cookies). Migration rung v1→v2 imports legacy `[general] session-key` config values into this table; config copies are now warned as unused. All token types ride one serializer — which is exactly why unsign sites shape-check payloads (see edit-cookie-shape capsule).
**Invariant:** The key's durability is a FEATURE (stable tokens across restarts) and a liability (DB leak = forgery of admin session too). Rotating means invalidating every outstanding link simultaneously.
**Probe:** `grep -c 'session-key' isso/db/preferences.py | wc -l` (`3`).
**Test:** `isso/tests/test_db.py:test_session_key_migration`, `test_defaults`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "preferences session key URLSafeTimedSerializer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt DB-persisted signing secrets with one-time random mint. Adapt storage to your KV. Always inventory payload shapes sharing a signer before adding a new token type.
