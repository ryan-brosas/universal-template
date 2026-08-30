<!-- capsule-v2 -->
# Skills modal input arbitration — a busy latch and three focus areas route every keypress, and closing mid-async must stop renders without leaking the in-flight action

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** One TUI modal owns a search input, a list, and a filter panel over the same keystrokes — how do you dispatch keys so no state machine ever double-handles an escape, and what happens if the user closes while a batch action is still running?

## SkillsManagerModal.handleInput
**Path/Symbol:** `src/handlers/skills-command.ts` — `handleInput` (:993–1105), guard order: `closed` (:994) → `busy` (:996–999) → `pendingDeleteConfirm` (:1001–1015) → `focusArea==="filters"` (:1017) → global esc (:1022) → per-area routing (search :1027–1037; list verbs from `MEMORY_SKILLS_KEYMAP` :23–35); `runAsyncAction` (:939–961), `closeModal` (:867–871), `syncSearchFocus` (:682–684), printable redirect test `isPrintableInput` + verb exclusion list (:989–991, :1102–1104).
**Signature:** `handleInput(data: string): void`; `runAsyncAction(action: Promise<SkillBatchActionResult>): Promise<void>`.
**Data Shape:** `busy: boolean` latch; `pendingDeleteConfirm: {skillIds} | null` two-keystroke arm/confirm state (`y` executes, `n`/esc cancels — anything else ignored); `focusArea: "search"|"list"|"filters"`.

### Decisive source
```ts
private async runAsyncAction(action: Promise<SkillBatchActionResult>): Promise<void> {
  if (this.closed) return;
  this.busy = true;
  this.summaryLines = ["Applying skill changes…"];
  this.tui.requestRender();
  try {
    const result = await action;
    if (this.closed) return;          // closed DURING await: drop result silently, no render
    this.setRows(result.skills, result.retainSelectedSkillIds, result.focusSkillId);
    this.summaryLines = result.summaryLines;
  } catch (error) {
    if (!this.closed) this.summaryLines = [error instanceof Error ? error.message : String(error)];
  } finally {
    this.busy = false;
    if (!this.closed) this.tui.requestRender();
  }
}
```
While `busy`, ONLY esc works (close); every other key is swallowed (:996–999). In list focus, single printable chars NOT in the reserved verb set `{g,p,d,a,n,f,s}` are redirected to the search input as typed text (:1102–1104) — `/` and tab focus search without consuming input (:1048–1051).

**Flow:** every render path re-reads `filteredRows` (category filter THEN fuzzy query), and cursor ops clamp via `Math.min(selectedIndex, rows.length-1)` after each rebuild (:686–694, :707–721). Filter panel edits a CLONE (`pendingFilters`); enter applies through `ensureValidFilters` which restores all-on when everything was toggled off (:109–112, :881–898); esc discards. Sort cycling rebuilds rows but re-focuses the previously current row by id (:759–785).
**Invariant:** after `closed`, the object keeps draining its promise but must not mutate UI state — `requestRender` calls are gated on `!this.closed` everywhere including `finally`. A porter who unconditionally renders in the finally-block resurrects a dismissed overlay. The verb-exclusion list MUST stay in sync with `MEMORY_SKILLS_KEYMAP` or typed letters get eaten as commands.
**Probe:** `tests/handlers/skills-command.test.ts` — "stops rendering updates after close during async actions" (:459, resolves the move AFTER close, asserts render count frozen), "uses in-modal delete confirmation and cancels with n" (:401), "supports in-modal category filters" (:493), "redirects printable keys to search from list focus" (:382).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "SkillsManagerModal runAsyncAction handleInput pendingDeleteConfirm focusArea", limit: 5 })`

## Verdict
Adopt for any multi-area TUI overlay with async actions. Adapt keymap letters; keep the guard ORDER (closed→busy→pending→area), the close-during-await render gate, and the clone-commit filter draft. Omit nothing.
