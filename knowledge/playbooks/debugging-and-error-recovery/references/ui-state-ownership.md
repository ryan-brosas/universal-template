# Debug unintended UI state changes

Use this when a filter, tab, selection, sort, expansion, or draft changes after an
action that does not visibly edit that control.

## Test ownership before patching effects

Classify the control before changing code:

- **User-owned:** a product default, restored user choice, or direct interaction
  establishes the value. Unrelated context changes must not replace it.
- **Derived:** another authority defines the value, so every authoritative change
  should propagate. The control has no independent choice to preserve.
- **Transition-owned:** a named boundary intentionally resets the value, such as
  leaving an account or opening a new document. Encode that transition explicitly.

A common failure joins two individually valid facts: an action correctly updates
ambient context, and an effect mirrors that context into a user-owned control.

## Trace and repair

1. Reproduce across two contexts. Record the control before the action, the action,
   the ambient state it changes, and the control afterward. Include the untouched
   default; testing only an explicit pick can hide the defect.
2. Trace both sides of the write chain: follow the action handler to its state
   mutations, then find every initializer, setter, reducer branch, effect, URL sync,
   persistence restore, and remount that can write the control.
3. State the invariant and authorized writers in one sentence: “Opening X may
   change Y; only A, B, or boundary C may change this control.”
4. Fix the lowest owner. For user-owned state, remove ambient context from its
   initializer and synchronization effects. Do not add a `pinned` or
   `hasInteracted` flag when the untouched default must also survive; that protects
   only the post-interaction case and leaves the original coupling intact.
5. Reconcile only validity when the available choices change:

   ```ts
   setSelection((selected) =>
     authoritativeOptions.has(selected) ? selected : fallback
   )
   ```

   If a route, workspace, or account really owns a reset, perform it at that named
   transition instead of inferring it from any context update.
6. Check every caller and writer after the edit. Remove obsolete pinning paths and
   duplicate sources of truth rather than leaving dormant synchronization logic.

## Guard the ownership boundary

Exercise this matrix where it applies:

- untouched default + unrelated context change → unchanged;
- explicit choice + unrelated context change → unchanged;
- chosen option removed from an authoritative set → fallback;
- intentional reset boundary → reset.

Prefer a real interaction test. If the UI renderer is unavailable, extract the
reconciliation decision into a pure function and test it, then add the narrowest
static dependency check that proves the control has no forbidden ambient writer.
Use source-text assertions only when that dependency is itself the contract, pair
them with a pre-fix or negative control when practical, and report that they do not
prove rendered behavior.

## Limits

Validity-only reconciliation is safe only when the option set is authoritative.
A temporarily empty or partial loading projection must not erase a valid choice.
URL-backed, parent-controlled, or intentionally context-following controls are
derived rather than user-owned. Also check component remounts: a correct local
initializer still resets if the parent replaces the component.
