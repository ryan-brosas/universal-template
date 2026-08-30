<!-- capsule-v2 -->
# Capability secret lifecycle — how do you encrypt form-field secrets on persist, reuse unchanged secret IDs, prune orphaned ones, and keep secrets encrypted in the live reference?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-core/.../internal/capability/DefaultCapabilityRegistry.java` + `CapabilityConfigurationSupport.java`); Codebase Memory `nexus-public`. **Question:** When a plugin config map contains password fields, how do you make sure plaintext never persists, unchanged values don't mint new secret records, and removed ones don't leak?

## Encrypt-on-write keyed by descriptor Encrypted fields; identity-reuse; prune-on-failure AND prune-after-success; decrypt ONLY at consumption
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/capability/DefaultCapabilityRegistry.java` — `encryptValuesIfNeeded` (:790–827), `pruneSecretsIfNeeded` (:832–857), `decryptValuesIfNeeded` (:884–910), `migrateValues` + `migrateSecrets` (:609–783), failure-path prunes (:231–234, :324–328); `public/common/components/nexus-capability/src/main/java/org/sonatype/nexus/capability/CapabilityConfigurationSupport.decryptSecret` (:101–132).
**Signature:** `private Map<String,String> encryptValuesIfNeeded(CapabilityDescriptor descriptor, Map<String,String> props, Map<String,String> oldProperties)`; `private void pruneSecretsIfNeeded(descriptor, persisted, toBePruned)`.
**Data Shape:** properties keyed by form-field id; only fields where `formField instanceof Encrypted` are touched. Values after encryption are SECRET IDs (e.g. `"0"`, `"_123"`), not ciphertext. `oldProperties` = the previously persisted encrypted map, used for reuse detection.

### Decisive source
```java
if (Objects.equals(oldSecretId, value)) {
  log.debug("Reusing existing secret for field {}", formField.getId());
  encrypted.put(formField.getId(), oldSecretId);            // UI round-tripped the ID: no new record
} else {
  String newSecretId = secretsService.encryptMaven("capabilities", value.toCharArray(), UserIdHelper.get()).getId();
  encrypted.put(formField.getId(), newSecretId);
}
```
```java
// add(): storage write failed ⇒ prune what we just created
catch (Exception e) { pruneSecretsIfNeeded(descriptor, Collections.emptyMap(), encryptedProps); throw e; }
// update(): success ⇒ prune the OLD value it replaced
pruneSecretsIfNeeded(reference.descriptor(), encryptedProps, reference.encryptedProperties());
```
```java
// load(): comment is the contract
// Do NOT decrypt secrets automatically - capabilities must decrypt on-demand
Map<String, String> properties = item.getProperties();
```

**Flow:** create/update: validate → `encryptValuesIfNeeded(props, oldProps)` (reuse if incoming == stored secret ID, else mint) → build storage item with ENCRYPTED map → try storage write; on exception prune the just-minted secrets and rethrow → on update success prune the replaced old secrets → hand BOTH maps to the reference (`properties`=plaintext view for callbacks, `encryptedProperties`=ID view). Load/refresh: NO decryption — the live reference's `properties()` returns the ENCRYPTED map; capabilities call `decryptSecret(secretId, store, service)` when they actually need the value (null-safe, missing-service-tolerant, underscore-prefix-stripping, NumberFormatException⇒return-as-is backwards compat). Migration task: re-encrypt via predicate, skip the storage write entirely if nothing changed.
**Invariant:** (1) Plaintext exists only transiently inside the registry call stack; persistence and `reference.properties()` hold secret IDs. (2) Every minted secret is paired with exactly one prune attempt on every exit path — failure paths prune the NEW ids, success paths prune the REPLACED ids. Prune failures log-and-continue (orphaned secrets are reclaimed by later maintenance, never fatal). (3) Reuse detection compares against the OLD PERSISTED id, so a UI echoing back the ID doesn't fork secret records. (4) On-demand decryption degrades gracefully: invalid/legacy plain values return as-is instead of throwing.
**Probe:** `DefaultCapabilityRegistryTest.java` — `updateWithEncryptedProperty_reuseExistingSecret` (~:886+: same ID ⇒ `encryptMaven` called once), `migrateCapabilityWithSecrets` (:628–671: predicate-true re-encrypts + updates; predicate-false skips the update because maps compare equal), `refreshReferencesOnDemand` (:587–628 asserts `properties().get("password")` equals the ENCRYPTED id after refresh).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "encryptValuesIfNeeded pruneSecretsIfNeeded decryptSecret migrateSecrets", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt descriptor-driven field classification (`instanceof Encrypted` ⇒ your schema marks secret fields), ID-based persistence with reuse detection, paired prune-on-every-exit-path, and lazy decrypt-at-consumption with legacy-value tolerance. Adapt the secrets service API and the audit attribution (`UserIdHelper.get()`). Omit the Maven-flavored `encryptMaven` keyring naming and OrientDB-era migration task scheduling.
