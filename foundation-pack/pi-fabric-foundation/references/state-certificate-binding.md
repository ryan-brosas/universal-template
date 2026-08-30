<!-- capsule-v2 -->
# State certificate binding — how do you persist a "current" certification so that persisting it can never make itself stale, and revoke it before announcing failure?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when a verification result must survive event-log truncation next to a CAS head, how do you bind it to the right version and keep failure from preserving stale success?

## Post-write version pre-binding + identity-gated revocation-before-publication
**Path/Symbol:** `src/state/store.ts`: `persistCurrentCertificate` (:1222-1263), `revokeCurrentCertificate` (:1265-1292); fold-side consumers `toCertificate` (:318-369), `durableCurrentCertificate` (:371-422). Direct tests: `tests/state-provider.test.ts` :306, :341, :379, :949, :1043, :1081, :1168 (suite 30/30 GREEN).
**Signature:** `persistCurrentCertificate(certificate, verificationHead, identity): Promise<StateCertificate>` (returns `current: true|false` variant); `revokeCurrentCertificate(verificationHead, identity): Promise<void>`.

### Decisive source
```ts
const nextVersion = current.version + 1;
const durableCertificate: StateCertificate = {
  ...certificate,
  head: { ...certificateHead, version: nextVersion },   // bind to the POST-write version
  current: true,
};
const written = await this.store.put({ key: CURRENT_KEY,
  value: { ...currentValue, certificate: durableCertificate },
  ifVersion: current.version, identity });
return written.version === nextVersion ? durableCertificate
                                       : { ...durableCertificate, current: false };
// revoke: identity-gated, then strip:
const { certificate: _certificate, ...withoutCertificate } = currentValue;
await this.store.put({ key: CURRENT_KEY, value: withoutCertificate, ifVersion: current.version, identity });
```

**Flow:** persisting requires the live head to still be EXACTLY the verified head (version + transitionId + label + destination all equal). The certificate's embedded `head.version` is computed as the CAS's own post-write version BEFORE writing, so the durable record describes the state that exists after the very write storing it — persistence cannot make itself stale. If a concurrent writer wins, the loser's record is returned with `current: false`: still a valid certificate OF ITS TARGET, just not of the new head. Revocation is identity-gated (only strips a certificate sitting on exactly the matching head) and runs BEFORE violation publication — docs/state-layer.md :193: ordering guarantees a publication failure can never preserve an old current certificate. Protocol-2 committed heads plus their one synthesized transition record plus their latest persisted certificate are readable independent of the bounded mesh event window (`maxReadEvents=5` tested at :949; certificate retained past the default 500-event window at :1081); after a later failed verification AND event aging, the durable revocation keeps it gone (:1043).
**Invariant:** `certification.current` is true only when the complete recorded head identity equals the committed current head; a later `state.violated` removes the overlay; CAS errors during revoke are swallowed (best-effort) while non-CAS storage errors throw.
**Probe:** executed byte-for-byte: `grep -n "nextVersion = current.version + 1" src/state/store.ts` → :1240; `grep -nF '{ certificate: _certificate, ...withoutCertificate }' src/state/store.ts` → :1281; suite GREEN (state-provider 30/30).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "persistCurrentCertificate revokeCurrentCertificate durable current certificate head binding stale", limit: 6 });
```
(Rank #1–3 resolve `persistCurrentCertificate` :1222-1263, `revokeCurrentCertificate` :1265-1292, `durableCurrentCertificate` :371-422 line-exact.)

## Verdict
Adopt post-write version pre-binding for any credential/certification stored beside a CAS-managed pointer, full-identity match guards before overlay or revoke, and revoke-before-announce ordering for failure paths; adapt identity fields (id/label/destination/version) to your head shape; omit retention-independence machinery if your event log never truncates under your reads — otherwise a bounded-window read will silently drop the very proof you just wrote.
