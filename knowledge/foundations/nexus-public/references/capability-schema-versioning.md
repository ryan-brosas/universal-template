<!-- capsule-v2 -->
# Capability schema versioning — how do you migrate persisted plugin config across descriptor versions at load time, and how does validation differ between CREATE, UPDATE, LOAD, and DELETE?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-capability/.../CapabilityDescriptor.java` + `DefaultCapabilityRegistry.load`); Codebase Memory `nexus-public`. **Question:** How do you evolve a plugin's configuration schema without breaking instances persisted under older schemas — and which lifecycle moments validate with which strictness?

## Version-stamped storage + convert-on-load + ValidationMode-grouped rules
**Path/Symbol:** `public/common/components/nexus-capability/src/main/java/org/sonatype/nexus/capability/CapabilityDescriptor.java` — `validate(id, properties, ValidationMode)` (:83), `version()` (:91), `convert(properties, fromVersion)` (:101), `enum ValidationMode` (:103–121) with grouping-class payload, `isDuplicated` (:128); `DefaultCapabilityRegistry.load` conversion block (:530–555) and LOAD-time validation (:569–578).
**Signature:** `Map<String,String> convert(Map<String,String> properties, int fromVersion)`; `void validate(@Nullable CapabilityIdentity id, Map<String,String> properties, ValidationMode validationMode)`.
**Data Shape:** each stored item carries `version` (the descriptor version that wrote it). ValidationMode members: CREATE, CREATE_NON_EXPOSED, UPDATE, LOAD, DELETE, DELETE_NON_EXPOSED — each wraps a marker class so validators can group rules per mode (`getGroupingClass()`).

### Decisive source
```java
// load(): convert stale-schema items BEFORE anything else consumes them
if (descriptor.version() != item.getVersion()) {
  try {
    properties = descriptor.convert(properties, item.getVersion());
    if (properties == null) { properties = Collections.emptyMap(); }
  }
  catch (Exception e) {
    log.error("Failed converting capability '{}' ... Capability will not be loaded", ...);
    continue;                                   // skip, never abort the whole registry load
  }
  capabilityStorage.update(id, capabilityStorage.newStorageItem(   // write-back migrates in place
      descriptor.version(), item.getType(), item.isEnabled(), item.getNotes(), properties));
}
...
try {
  // validate after initial load, so properties are filled in for fixing
  reference.descriptor().validate(id, properties, ValidationMode.LOAD);
}
catch (ValidationException e) {
  log.warn("Capability '{}' of type '{}' with properties '{}' is invalid", ...);
  reference.setFailure("Load", e);              // flag in UI, keep it loaded
}
```

**Flow:** registry `load()`: unknown type ⇒ INFO-skip (forward compatibility); version mismatch ⇒ convert → null-map normalize → persist the migrated item immediately (lazy one-time migration) → create/load reference → validate with LOAD mode ⇒ failure only latches a UI-visible error, the capability still loads. Create path validates with CREATE (or CREATE_NON_EXPOSED via `addNonExposed`), update with UPDATE (:314), delete-non-exposed re-validates with DELETE_NON_EXPOSED before removal (:409).
**Invariant:** (1) Conversion failures isolate to ONE capability — `continue`, never throw out of the loop; a bad migration cannot take down every capability. (2) LOAD-mode validation is advisory (failure latched, instance loaded) while CREATE/UPDATE-mode validation is blocking (exceptions propagate from add/update). (3) The descriptor version must change whenever its fields change — that contract is what makes the persisted stamp meaningful. (4) Migration is write-back-once: after load, the item's version equals the descriptor's, so subsequent loads are no-ops.
**Probe:** `DefaultCapabilityRegistryTest.java` — duplicate/unknown-type tolerance `loadWhenCapabilityIsNotUnique` (:552–573: both duplicates load, `hasFailure()==false`); LOAD-mode latch behavior pinned indirectly through `reference.setFailure("Load", …)` wiring exercised by DefaultCapabilityReferenceTest failure-latch cases. Coverage caveat: no dedicated test drives a real `convert()` implementation; conversion semantics rest on the source contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "ValidationMode convert version descriptor capability load", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt versioned persisted config + convert-on-load with per-item isolation and one-time write-back, plus mode-grouped validation where LOAD is non-blocking. Adapt the marker-class grouping idiom to your validation framework. Omit the ExtDirect/UI exposure flags (isExposed/isHidden) that motivated CREATE_NON_EXPOSED vs CREATE.
