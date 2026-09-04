<!-- capsule-v2 -->
# Transfer-refused UI halt — how do you keep a Filament action modal open after a caught business refusal?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** When an action closure catches its own domain exception and shows a danger notification, how do you stop the framework from dismissing the modal as if it succeeded?

## Narrow exception + $action->halt() pairing
**Path/Symbol:** `packages/SystemAdmin/src/Filament/Resources/SubscriptionResource.php` :202-219 (`->action(function (array $data, Subscription $record, TransferWorkspaceBilling $transfer, Action $action)`), :236 `transferTargets(Subscription $record)`; exception at `packages/SystemAdmin/src/Exceptions/TransferRefused.php` :15.
**Signature:** `TransferRefused extends RuntimeException` (final, marker class); action closure injects BOTH the service AND the `Action` itself via container resolution of the closure signature.
**Data Shape:** Option list pre-filter = `Team::where('user_id', source)->whereKeyNot(source)->whereNull('stripe_id')->whereNull('scheduled_deletion_at')->orderBy('name')->pluck('name','id')`.

### Decisive source
```php
} catch (TransferRefused $exception) {
    Notification::make()
        ...
        ->send();

    $action->halt();
}
```
(:211-218). Commit-message rationale: "Filament dismisses an action's modal after any non-halting completion, including a caught business refusal. Inject the Action into the transfer closure and call halt() after the danger notification so the operator sees the error without having to reopen the modal and re-pick a target." The narrow-exception commit message adds: catching a bare RuntimeException swallowed infrastructure failures such as ModelNotFoundException and QueryException — both RuntimeException subtypes — and reported them to the operator as business-rule refusals instead of letting them propagate to error tracking.

**Flow:** visible gate hides the action entirely on invalid subscriptions or empty target lists (:184 `visible(fn (Subscription $record) => $record->valid() && self::transferTargets($record) !== [])`) → Select options exclude ineligible targets → a race that makes a target ineligible between render and submit falls through to execute()'s assertTransferable → catch TransferRefused ONLY → notify + halt (modal stays open, state intact) → any other Throwable propagates to error tracking untouched.
**Invariant:** UI option-list filtering is UX, not authorization: guards must be re-enforced in the action itself because option lists are validated only as form input. Tests named for a guard that only exercise the option-list rejection prove nothing about the guard — direct-call tests resolving the action from the container are required.
**Probe:** `tests/Feature/SystemAdmin/SubscriptionTransferActionTest.php` (:264/:284 option-list exclusion tests renamed to say what they actually prove; :302/:315/:362 direct-call guard tests; :375 `assertActionHalted` pins the modal-stays-open behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "transferAction halt TransferRefused transferTargets", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the trio (marker exception for operator-actionable failures / halt-after-notification / guards duplicated under the option list); adapt notification copy; omit Relaticle's subscription domain. Direct tests cover every refusal polarity including the halted modal.
