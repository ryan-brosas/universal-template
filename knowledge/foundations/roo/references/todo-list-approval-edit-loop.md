<!-- capsule-v2 -->
# update_todo_list approval-edit loop — how can the human rewrite a tool's proposal AFTER clicking approve?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What mechanism lets the webview edit a todo list during the approval ask, and how does the model find out its proposal was overridden?

## approvedTodoList slot — stash before ask, compare after
**Path/Symbol:** `src/core/tools/UpdateTodoListTool.ts:execute` (19–87) + module slot line 14 + `setPendingTodoList` (204–206); write-back `src/core/webview/webviewMessageHandler.ts:1674–1681`.
**Signature:** `execute(params: {todos: string}, task, callbacks)`; `export function setPendingTodoList(todos: TodoItem[])`; parser `parseMarkdownChecklist(md: string): TodoItem[]` (178–202).
**Data Shape:** `todos` arrives as a MARKDOWN CHECKLIST STRING; items `{id, content, status: "pending"|"in_progress"|"completed"}`; checklist grammar `/^(?:-\s*)?\[\s*([ xX\-~])\s*\]\s+(.+)$/` with `x/X→completed`, `-/~→in_progress`, else pending.

### Decisive source
```ts
approvedTodoList = cloneDeep(normalizedTodos)
const didApprove = await askApproval("tool", approvalMsg)
if (!didApprove) { pushToolResult("User declined to update the todoList."); return }

const isTodoListChanged =
    approvedTodoList !== undefined && JSON.stringify(normalizedTodos) !== JSON.stringify(approvedTodoList)
if (isTodoListChanged) {
    normalizedTodos = approvedTodoList ?? []
    task.say("user_edit_todos", JSON.stringify({ tool: "updateTodoList", todos: normalizedTodos }))
}
await setTodoListForTask(task, normalizedTodos)
if (isTodoListChanged) {
    const md = todoListToMarkdown(normalizedTodos)
    pushToolResult(formatResponse.toolResult("User edits todo:\n\n" + md))
}
```
```ts
// webviewMessageHandler.ts — the UI's edit lands in the same slot while ask() is pending
case "updateTodoList": {
    const payload = message.payload as { todos?: any[] }
    const todos = payload?.todos
    if (Array.isArray(todos)) { await setPendingTodoList(todos) }
    break
}
```

**Flow:** parse markdown → validateTodos (id/content required; status checked against todoStatusSchema.options) → normalizeStatus fails safe to "pending" → stash cloneDeep into module-global approvedTodoList → ask → webview "updateTodoList" message may overwrite the slot mid-ask → after resolution, JSON.stringify comparison detects the edit → user version WINS, say("user_edit_todos") fires, and the tool RESULT tells the model "User edits todo:\n\n<markdown>".
**Invariant:** (1) The slot is MODULE-GLOBAL and written by two processes (extension tool + webview handler); correctness rests on stash-BEFORE-ask and the post-ask comparison — no lock. (2) The model is never left believing its proposal was applied verbatim: the override is surfaced in-band as tool output plus a user_edit_todos narration. (3) Identity is dual-regime: parseMarkdownChecklist mints `md5(content+status)` ids (status change ⇒ NEW id), programmatic addTodoToTask uses crypto.randomUUID(); updateTodoStatusForTask allows ONLY pending→in_progress, in_progress→completed, or same-status writes (no backward/skip). (4) handlePartial parses the same grammar but degrades to [] on failure instead of erroring, so streaming previews never crash.
**Probe:** runner BLOCKED. Direct spec exists (`src/core/tools/__tests__/updateTodoListTool.spec.ts`) covering parse/normalize/transition helpers. Deterministic source pins from repo root: `grep -c 'let approvedTodoList' src/core/tools/UpdateTodoListTool.ts` → 1; `grep -c 'await setPendingTodoList(todos)' src/core/webview/webviewMessageHandler.ts` → 1; `grep -c 'md5' src/core/tools/UpdateTodoListTool.ts` → 1; `grep -c 'User edits todo:' src/core/tools/UpdateTodoListTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "Roo-Code", function_name: "Roo-Code.src.core.tools.UpdateTodoListTool.setPendingTodoList", direction: "inbound" });
```

## Verdict
Adopt the stash-compare slot whenever a host lets users annotate/edit an approval payload mid-ask; adopt in-band override reporting to the model. Adapt storage of the slot (module global is fine single-window; use per-task state multi-window). Omit nothing silently — dropping the user_edit_todos say breaks UI sync even though setTodoListForTask already stored the edit. Caveat: spec covers helper functions, not the full edit-loop integration; loop pinned via trace_path + source reads at this pin.
