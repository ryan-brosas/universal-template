<!-- capsule-v2 -->
# Fun undo composition kernel — how do you make every model mutation undoable without double-executing it?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must thread undo/redo through thousands of small mutations without writing a QUndoCommand subclass per operation, and must not let QUndoStack's push-time implicit redo() re-apply an already-executed change.

## Functor accumulation over a lambda pair
**Path/Symbol:** `src/macros.hpp:PUSH_UNDO/UPDATE_UNDO_REDO/LOCK_IN_LAMBDA` (lines 23–78), `src/undohelper.hpp:Fun/PUSH_LAMBDA/FunctionalUndoCommand` (10–44), `src/undohelper.cpp:FunctionalUndoCommand::undo/redo` (22–43), `src/doc/docundostack.cpp:DocUndoStack::push` (16–22).
**Signature:** `using Fun = std::function<bool(void)>;` · `void PUSH_UNDO(undo, redo, text)` (macro) · `UPDATE_UNDO_REDO(operation, reverse, undo, redo)` (macro) · `FunctionalUndoCommand(Fun undo, Fun redo, const QString &text, QUndoCommand *parent = nullptr)`.
**Data Shape:** Two accumulator lambdas (`undo`, `redo`) start as `[](){return true;}` and grow inside a request method; every atomic step contributes its forward action to `redo` and its reverse to `undo`. The class owning the macros must expose `std::weak_ptr<DocUndoStack> m_undoStack` and a recursive `mutable QReadWriteLock m_lock`.

### Decisive source
```cpp
// undohelper.hpp — the redo latch
/** Note that QUndoStack actually executes redo() when we push the undoCommand to the stack
  This is bad for us because we execute the command as we construct the undo Function. So to prevent it to be executed twice, there is a small hack in this
  command that prevent redoing if it has not been undone before. */
void FunctionalUndoCommand::redo()
{
    if (m_undone) {
        bool res = m_redo();
        Q_ASSERT(res);
    }
    QUndoCommand::redo();
}
// macros.hpp — composition direction
#define UPDATE_UNDO_REDO_NOLOCK(operation, reverse, undo, redo)                                                \
    undo = [reverse, undo]() { bool v = reverse(); return undo() && v; };                                      \
    redo = [operation, redo]() { bool v = redo(); return operation() && v; };
```

**Flow:** request method starts `undo/redo` identity functors → executes each atomic step eagerly → after each success composes it via UPDATE_UNDO_REDO (reverse∘undo, redo∘operation), each arm lock-wrapped by LOCK_IN_LAMBDA → on final success `PUSH_UNDO` wraps the pair in FunctionalUndoCommand and pushes through the weak_ptr'd DocUndoStack → QUndoStack::push calls redo(), which the `m_undone=false` latch suppresses → user undo sets `m_undone=true`, runs `m_undo()`, asserts true.
**Invariant:** The operation has ALREADY been applied by the time the command is pushed; the latch guarantees exactly-once semantics across push/undo/redo, and any functor returning false trips `Q_ASSERT(res)` in debug (fail-loud corruption detection). `DocUndoStack::push` emits `invalidate(index())` whenever a redo branch (`index() < count()`) is about to be truncated.
**Probe:** `tests/movetest.cpp:82-94` — cut then `undoStack->undo(); undoStack->redo();` preserves per-track producer identity (`prod3.same_clip(prod4)` false cross-track, `prod1.same_clip(prod3)` true same-track); `tests/trimmingtest.cpp:162-173` — three undos restore exact positions/playtimes, three redos re-reach state3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "pushUndo DocUndoStack", limit: 16 });
// executed live: rank 1 kdenlive.src.core.Core.pushUndo core.cpp:1406-1409;
// rank 2 DocUndoStack.DocUndoStack docundostack.cpp:10-13; rank 3 DocUndoStack.push :16-22
```

## Verdict
Adopt the two-accumulator functor discipline, the m_undone latch, and invalidate-on-truncation verbatim — they are host-independent. Adapt `PUSH_UNDO`'s weak_ptr lookup and i18n text to your DI/logging stack. Omit the CRASH_AUTO_TEST Logger hooks and Qt QUndoGroup parenting unless your host already runs QUndoStack.
