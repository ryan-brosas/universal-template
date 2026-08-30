<!-- capsule-v2 -->
# Webhook secret storage & unsubscribe-key auth — where do webhook URL/auth/unsubscribeKey live, and how is third-party deletion authorized?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are per-webhook credentials persisted so DocApi can update them while outsiders can only delete with a proof?

## One Secret row per webhook holding JSON {url, authorization, unsubscribeKey}; patch semantics preserve undefined fields; unsubscribe requires key match
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `addSecret` (:1804–1813), `updateSecret` (:1816–1825, affected!==1 → 404), `getSecret` (:1827–1834), `updateWebhookUrlAndAuth` (:1838–1866), `removeWebhook` (:1868–1892).
**Signature:** `updateWebhookUrlAndAuth({id, docId, url?, auth?, outerManager?})`; `removeWebhook(id, docId, unsubscribeKey, checkKey)` — missing id → 400; checkKey without key → 400; wrong key → 401 "Wrong unsubscribeKey".
**Data Shape:** Secret.value = JSON string of `WebHookSecret {url?, authorization?, unsubscribeKey?}`; row identity = (id uuid, doc_id). Patch rule: only DEFINED fields overwrite ("When the user wants to empty the value, we are expected to receive empty strings") — undefined means keep.

### Decisive source
```ts
const value = await this.getSecret(id, docId, manager);
if (!value) { throw new ApiError("Webhook with given id not found", 404); }
const webhookSecret = JSON.parse(value);
// ...only set the url and the authorization when they are defined.
if (url !== undefined) { webhookSecret.url = url; }
if (auth !== undefined) { webhookSecret.authorization = auth; }
await this.updateSecret(id, docId, JSON.stringify(webhookSecret), manager);
```
```ts
public async removeWebhook(id: string, docId: string, unsubscribeKey: string, checkKey: boolean): Promise<void> {
  ...
  if (checkKey) {
    const secret = await this.getSecret(id, docId, manager);
    if (!secret) { throw new ApiError("Webhook with given id not found", 404); }
    const webhook = JSON.parse(secret) as WebHookSecret;
    if (webhook.unsubscribeKey !== unsubscribeKey) {
      throw new ApiError("Wrong unsubscribeKey", 401);
    }
  }
```

**Flow:** webhook creation (DocApi plane, see webhook-registration-choreography) mints the Secret row; updates go through runInTransaction(outerManager) to compose with caller transactions; removal hard-deletes the Secret row inside its own transaction. The existing webhook-secret-splitbrain capsule covers delivery-side consistency; THIS seam is the storage/auth contract.
**Invariant:** Unsubscribe-key checking is OPTIONAL by design (`checkKey`) — authenticated doc-owner deletes skip it, unauthenticated unsubscribe links require it; the same endpoint serves both. A porter who always requires the key breaks owner UX; one who never checks it hands anyone-with-the-id deletion power.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -c "unsubscribeKey" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 3.
`bash -c 'grep -rn "Wrong unsubscribeKey" test/ | head -2'` → coverage exists.
Direct tests: `test/server/lib/docapi/Webhooks.ts` (unsubscribe + secret round-trip its).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"updateWebhookUrlAndAuth removeWebhook addSecret WebHookSecret unsubscribeKey","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — complements the two existing webhook capsules with the home-DB credential-row contract they reference but don't pin.
