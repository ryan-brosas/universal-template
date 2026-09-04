<!-- capsule-v2 -->
# Webhook secrets split-brain — where do webhook URL + authorization header live so they never enter the document?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** A trigger row lives inside the shared document that forks/copies flow through — how do you keep its credentials out of it while keeping GET responses complete?

## Doc stores {type,id} references; homeDB secret row stores url+authorization+unsubscribeKey; merge on read
**Path/Symbol:** `app/server/lib/DocApiTriggers.ts`: `ACTION_SECRET_FIELDS` (43), `ACTION_TYPES_WITH_SECRETS` (46), `extractSecrets` (84–98), `createActionSecret` (120–137), `extractAndUpdateActionSecret` orphan-heal (145–165), `loadActionSecrets` (171–186), `removeSecret` → removeWebhook (192–200).
**Signature:** `createActionSecret(action, dbManager, docId): Promise<TriggerAction>`; `loadActionSecrets(action, dbManager, docId)`; secret payload = `JSON.stringify(WebHookSecret)` keyed by server-generated UUID.
**Data Shape:** doc-side action after processing = `{ type: "webhook", id: <secret uuid> }` (+ non-secret fields); homeDB side = `{ unsubscribeKey, url, authorization }`.

### Decisive source
```ts
for (const [key, value] of Object.entries(action)) {
  if ((ACTION_SECRET_FIELDS as readonly string[]).includes(key)) { secretData[key] = value; }
  else { docAction[key] = value; }
}
// create: user-supplied ids IGNORED — "IDs are always server-generated to prevent storing
// secrets with non-standard or insecure keys"; unsubscribeKey minted if absent.
// update heal:
const existing = await dbManager.getSecret(action.id, docId);
if (!existing) {
  // Orphaned secret (e.g. after copy/fork): heal by creating a fresh one rather
  // than letting updateSecret throw 404 and abort sibling actions in the batch.
  return await createActionSecret(action, dbManager, docId);
}
await dbManager.updateSecret(action.id, docId, JSON.stringify({ ...existingData, ...secretData }));
```

**Flow:** POST/PATCH splits each action into doc part + secret part → secret upserted into homeDB keyed by the id embedded in the document's `_grist_Triggers.actions` JSON → GET (`/triggers` list) re-merges secret fields back into every returned action; unreadable secret JSON logs a warning and returns the action unmerged (never 500). Removal goes through `removeWebhook(secretId, docId, unsubscribeKey, checkKey)` — the ONLY deletion path; non-owner callers must present the unsubscribe key.
**Invariant:** the document is copy/fork-safe precisely because secrets never ride in it — which means a copied doc has dangling ids, and EVERY update path must tolerate that by healing (new secret) instead of failing the batch. Secret-bearing actions are recognized by TYPE membership (`webhook`), not field shape; email-type actions always get a bare UUID with no homeDB row.
**Probe:** `test/server/lib/docapi/DocApiTriggers.ts:136` "should update trigger with webhook action and store secrets", :259 "PATCH /triggers heals orphaned webhook secret on a copied doc".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "addSecret getSecret removeWebhook extractSecrets loadActionSecrets", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenever user-managed callback credentials must survive inside replicated/synced documents: store a reference in the data plane, the credential in a control-plane side table scoped by (id, owner-doc). Adapt the healing policy — upstream heals silently on update and leaves reads unmerged-but-200. Omit per-action-type registries if you only have one secretful action kind.
