<!-- capsule-v2 -->
# Verify-tail suppression split — where do suppressed messages go after `verify()`, and how do they interact with the autofix loop?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (tag v10.9.0); Codebase Memory project `eslint`. **Question:** A porter must know exactly which problems reach callers and which are parked for later inspection.

## Verify-tail partition point

**Path/Symbol:** `lib/linter/linter.js:Linter._distinguishSuppressedMessages` (:1429-1445), `Linter.getSuppressedMessages` (:1475-1477), verify tail (:860-867), internal-slot init (:795), `Linter.verifyAndFix` (:1488-1565).
**Signature:** `_distinguishSuppressedMessages(problems: Array<LintMessage|SuppressedLintMessage>): LintMessage[]`.
**Data Shape:** Each problem may carry `suppressions: Array<{kind: "directive"|"config"|"suppression", justification?: string}>`. Suppressed entries are stored on the private `internalSlotsMap` slot `lastSuppressedMessages` (initialized `[]`).

### Decisive source

```js
	_distinguishSuppressedMessages(problems) {
		const messages = [];
		const suppressedMessages = [];
		const slots = internalSlotsMap.get(this);

		for (const problem of problems) {
			if (problem.suppressions) {
				suppressedMessages.push(problem);
			} else {
				messages.push(problem);
			}
		}

		slots.lastSuppressedMessages = suppressedMessages;

		return messages;
	}
```

**Flow:** `verify()` returns `_distinguishSuppressedMessages(_verifyWithFlatConfigArray(...))`, so EVERY result path (plain, processor, recursive processor blocks) funnels through one partition. The splitter parks anything with a `.suppressions` property into the slot and returns only clean messages. `verifyAndFix` calls `this.verify(...)` each pass, so `SourceCodeFixer.applyFixes` NEVER sees suppressed messages; the slot holds only the LAST pass's set (replaced, not appended), and the post-loop confirmation lint leaves the final text's suppression state in the slot.
**Invariant:** `verify()` output never contains a message carrying `.suppressions`; `getSuppressedMessages()` describes the most recent run only; a directive-suppressed fixable violation is neither fixed nor reported; a subsequent directive-free `verify()` resets the slot to `[]`.
**Probe:** `tests/lib/linter/linter.js` `describe("getSuppressedMessages()")` (:9634-9680; pins `suppressions: [{kind:"directive", justification:"justification"}]` shape). Executed: `npx mocha tests/lib/linter/linter.js --grep "getSuppressedMessages"` → 3 passing. Executed behavioral probe against a directive-suppressed `no-var`: verify → 0 messages, slot = 1 (`no-var|[{"kind":"directive","justification":"j"}]`); `verifyAndFix` → output unchanged, `fixed=false`, 0 reported messages, slot still 1 after loop; later clean verify → slot 0.

## Get live surrounding code

**Retrieve:**

```ts
await tools["mcp__codebase-memory__search_graph"]({ project: "eslint", name_pattern: "_distinguishSuppressedMessages|getSuppressedMessages", limit: 10, fields: ["lines"], format: "json" });
// → Linter methods at lib/linter/linter.js 1429-1445 / 1475-1477 (executed)
```

## Verdict

Adopt the partition-at-tail design: one choke point converts the raw problem stream into public messages plus a last-run suppressed side-channel. Adapt slot storage to your host's instance state mechanism. Omit nothing behavioral — but note the Webpack-driven duck-typing workaround above the tail (`getConfig` presence check) is bundler-specific context, not part of the contract. Coverage caveat: the suppression × max-fix-pass interplay beyond two passes was verified by source read of the loop, not by a dedicated multi-pass suppressed-fix test.
