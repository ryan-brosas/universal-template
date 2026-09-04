<!-- capsule-v2 -->
# connector-statefile-claim-guard-cas — how do two concurrent connector launches replace a dead instance's state file without ever double-claiming or corrupting a live one?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What is the crash-safe ladder from O_EXCL claim, through stale detection, to exactly-one-winner replacement — and how is pid reuse defeated?

## O_EXCL claim → dead-pid detection → generation-keyed guard chain of hard-linked ownership records → content CAS before rm+recreate; guards are succeeded, never deleted by contenders
**Path/Symbol:** `apps/cli/src/connectors/common.ts` (`tryClaimConnectorStateFile` :341-388, `tryCreateConnectorStateFile` :390-411, `tryReplaceStaleConnectorStateFile` :413-528) and `apps/cli/src/connectors/base.ts:maybeRunInBackground` (:314-377).
**Signature:** `tryClaimConnectorStateFile(statePath: string, createState: (claimId: string) => { claimId: string; pid: number } & Record<string, unknown>, processProbe?: ProcessProbe): { claimId: string } | undefined`.
**Data Shape:** State file = pretty JSON with `claimId`, `pid`, plus adapter state. Ownership record = `{ claimId, pid, processStartToken }` written to a `.candidate` file, then hard-linked into guard paths `${statePath}.${generation}.claim` where `generation = sha256(observedPayload)`.

### Decisive source
```ts
if (tryCreateConnectorStateFile(statePath, payload)) {
	return { claimId };
}
// ... read observed payload; live pid (with matching processStartToken) ⇒ undefined
const generation = createHash("sha256").update(observedPayload).digest("hex");
// link candidate into guard; on EEXIST inspect the guard owner:
if (typeof guardOwner.pid === "number" && processProbe.isRunning(guardOwner.pid)) {
	const runningStartToken = processProbe.getStartToken(guardOwner.pid);
	if (typeof guardOwner.processStartToken !== "string" ||
		runningStartToken === undefined ||
		runningStartToken === guardOwner.processStartToken) {
		return false; // live owner blocks replacement
	}
}
// dead owner ⇒ append a SUCCESSOR guard, never delete:
const successor = createHash("sha256")
	.update(guardPath).update("\0").update(guardPayload).digest("hex");
guardPath = `${statePath}.${generation}.${successor}.claim`;
// final content CAS:
if (readFileSync(statePath, "utf8") !== observedPayload) {
	return false;
}
rmSync(statePath);
return tryCreateConnectorStateFile(statePath, replacementPayload);
```

**Flow:** claim via `openSync(statePath, "wx")` (O_EXCL — two concurrent launches cannot both observe "no running instance") ⇒ EEXIST ⇒ read the observed payload; a live pid blocks (pid-reuse defeated by comparing the CURRENT `processStartToken` against the recorded one — a recycled pid gets a different start token) ⇒ stale ⇒ each contender writes its ownership record to a unique `.candidate` file and hard-links it into the generation-keyed guard path; EEXIST on the link means someone else holds the guard ⇒ inspect the guard owner: live ⇒ fail; dead ⇒ chain a SUCCESSOR guard named `sha256(guardPath + \0 + guardPayload)` (guards are never deleted by contenders, so stale recovery stays crash-safe) ⇒ guard acquired ⇒ re-read the state file and require it to still equal the observed payload (content CAS) ⇒ rm + recreate with the replacement payload ⇒ finally removes the candidate and, only if acquired, the guard chain. Detached launch (base.ts): foreground/interactive/supervised bypass; already-running prints the message and exits **75** (`CONNECT_ALREADY_RUNNING_EXIT_CODE`); spawn → poll state-file readiness every 100 ms up to 15 s → child death ⇒ "child exited before becoming ready" with a log-tail hint; timeout ⇒ terminate the child. The log hint reads the last 8192 bytes (`CHILD_LOG_TAIL_BYTES`), drops a partial first line when starting mid-file, strips ANSI, keeps the last 3 lines (`CHILD_LOG_TAIL_LINES`), and is best-effort — a missing log never turns a startup failure into a crash.
**Invariant:** At most one process owns a state path; replacement succeeds for exactly one contender per observed generation; a live guard owner (or a pid-reuse impostor) always blocks; guards are append-only across contender crashes.
**Probe:** `common.test.ts` (13 cases): "claims an empty path and rejects a second live claim", "replaces a dead-pid claim", "allows only one contender to replace the same stale generation", "recovers when a stale-generation guard owner exits before replacement", "does not succeed a live stale-generation guard owner", "recovers when an orphaned guard pid belongs to a different process". Probes: `grep -cF 'openSync(statePath, "wx")' common.ts` → 1; `grep -cF 'linkSync(candidatePath, guardPath)' common.ts` → 1; `grep -cF 'processStartToken' common.ts` → 4; `grep -cF 'CONNECT_ALREADY_RUNNING_EXIT_CODE = 75' common.ts` → 1; `grep -cF 'CHILD_LOG_TAIL_BYTES = 8_192' base.ts` → 1; `grep -cF 'child exited before becoming ready' base.ts` → 2.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "tryClaimConnectorStateFile guard generation hard link processStartToken stale replacement", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the O_EXCL claim, generation-keyed guard chain with successor guards, processStartToken pid-reuse defense, and content CAS before rm+recreate; adopt the poll-ready detached launch with exit-75 already-running and the best-effort ANSI-stripped log tail. Adapt the guard-path naming and the ProcessProbe to your OS. Omit Cline's log-rotation generations (commodity). Coverage: common.ts and base.ts read whole at pin; 13-case suite read whole.
