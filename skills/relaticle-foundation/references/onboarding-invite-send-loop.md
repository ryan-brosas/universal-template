<!-- capsule-v2 -->
# Onboarding invite send loop — how do you fan out N invitation mails in one request without a dead mail server burning the user's registration?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** What is the per-address failure taxonomy (invalid / transport-down / validation-refused) and the circuit-breaker rule that keeps a half-finished onboarding from stranding the user?

## sendOnboardingInvites: classify-never-throw + one-refusal circuit breaker
**Path/Symbol:** `app/Filament/Pages/CreateTeam.php` :554 `sendOnboardingInvites(User $user, Team $team, array $data)`.
**Signature:** private, called from handleRegistration AFTER the workspace exists; collects `$failed` list of `{email, reason}` instead of throwing.
**Data Shape:** invites = list of `{email: ?string, role: ?string}`; blank emails skipped silently; failures rendered as one warning notification body `"email: reason"` lines.

### Decisive source
```php
// Retrying a dead mail server once per address means waiting out the socket
// timeout up to five times inside this request. One refusal is enough.
$transportIsDown = false;
...
} catch (TransportExceptionInterface $exception) {
    // The workspace already exists by now, and the invitation row is written
    // before the send, so the owner can resend from settings. Letting this
    // escape would strand the user on a half-finished registration.
    report($exception);

    $transportIsDown = true;
    ...
}
```
(:562-624). Three failure classes with distinct reasons: (1) `filter_var($email, FILTER_VALIDATE_EMAIL)` false (:576) — the form's `email` rule is LOOSER than filter_var (accepts `user@example`), so an address can clear the form and still be unusable; reported, never silently dropped; (2) transport exception — `report()`ed to error tracking, marks the circuit open, remaining addresses get "send_skipped" (NEVER attempted, so there is no invitation row to resend: they must be invited from scratch once mail works); (3) ValidationException from InviteTeamMember — first flattened error becomes the reason (duplicate/already-member).

**Flow:** workspace creation has ALREADY committed by the time this runs → per address: blank→skip, invalid→failed(reason), circuit-open→failed(skipped), else invite() → TransportException ⇒ report + open circuit + failed(send_failed); ValidationException ⇒ failed(first error) → any failures ⇒ single aggregated warning notification.
**Invariant:** Invitation rows are written BEFORE the mail send, so a send failure leaves a resendable row for THAT address but nothing for later addresses never attempted — the two cases carry different reasons because their recovery paths differ. The loop must never rethrow: registration would strand mid-flow even though its durable work is done.
**Probe:** `tests/Feature/Onboarding/CreateTeamOnboardingTest.php` (:633 sends provided invites; :690 only-valid-invitations-when-some-empty; :838 warns-about-undeliverable-addresses-the-form-accepted; :863 finishes-onboarding-when-mail-transport-is-down).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "sendOnboardingInvites InviteTeamMember TransportExceptionInterface", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the taxonomy (looser-form-rule vs filter_var gap; skip-vs-failed distinction keyed to whether a durable row exists) and the one-refusal circuit breaker; adapt notification assembly; omit Jetstream invite specifics. Four direct tests cover the happy path and both terminal failure classes.
