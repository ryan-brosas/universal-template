<!-- capsule-v2 -->
# Invite link join + auto-verify ladder — how do token-based team joins resolve for every auth state, and how does an invited email skip verification?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** What is the complete decision ladder for `/teams/join/{token}` (expired token / scheduled deletion / already-member / join+switch) and its register-page twin that pre-fills and pre-verifies the invited address?

## JoinTeamViaLinkController resolve-once + unsetRelation-before-switch
**Path/Symbol:** `app/Http/Controllers/JoinTeamViaLinkController.php` :19 `show(Request,string)`, :39 `store(Request,string,AddsTeamMembers)`, :87 `resolveTeam(string $token): Team|View`.
**Signature:** both actions return `RedirectResponse|View` — a VIEW is the failure channel (expired-token page), so callers branch with `$team instanceof View`. `AcceptTeamInvitationController::__invoke` (`app/Http/Controllers/AcceptTeamInvitationController.php` :19) is the per-address-invitation twin: email-mismatch ⇒ Log::warning + abort(403); expired ⇒ warning page.
**Data Shape:** Team lookup by opaque `invite_link_token` column; expiry via `isInviteLinkTokenExpired()`; join always lands role Editor (:63).

### Decisive source
```php
$adder->add($owner, $team, $user->email, TeamRole::Editor->value);

$user->unsetRelation('teams');
$user->switchTeam($team);
```
(:59-67). The unsetRelation matters because belongsToMany `teams` may already be cached on the authed user; switchTeam consults the relation and would misjudge membership. resolveTeam orders its gates: expired-token view FIRST, then 410 for teams scheduled for deletion ("not accepting new members"), then 403 when the SIGNED-IN user's own account is scheduled for deletion. Already-member short-circuits in BOTH show() and store(): switch + "already_member" toast, never a re-add.

**Flow (register twin):** invitation stored in session by the guest-facing redirect chain → Register page pre-fills email from it (`app/Filament/Pages/Auth/Register.php` :62 `->default(fn () => $this->getTeamInvitationFromSession()?->email)` — retyping from memory would cost the user auto-verification) → handleRegistration (:84-98) creates user, then `if ($invitation && $invitation->email === $data['email'] && $user->markEmailAsVerified()) event(new Verified($user))` — EXACT-match gate, different address ⇒ normal verification flow → spam protection via spatie/honeypot (`protectAgainstSpam()` :68 replacing the deleted Cloudflare Turnstile rule/client — commit #515).
**Invariant:** One lookup, one gate order; the View-as-failure convention must stay consistent or callers re-fetch tokens twice. Auto-verification requires exact invited-address match AND markEmailAsVerified success — partial matches silently take the verify-later path (pinned by tests).
**Probe:** `tests/Feature/Teams/InvitationUxTest.php` (:92 registering-via-invitation-auto-verifies; :121 without-link-not-verified; :137 different-email-than-invitation-NOT-verified; :226 register-prefills-invited-email; :243 no-invitation-leaves-blank), `tests/Feature/Teams/InviteLinkExpiryTest.php` (:25/:32 expired true; :39 fresh false), `tests/Feature/Teams/InviteLinkTokenTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "JoinTeamViaLinkController resolveTeam switchTeam AcceptTeamInvitationController", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the auth-state ladder, View-as-failure channel, unsetRelation-before-switch, and exact-match auto-verify gate; adapt roles and mail flow; omit Relaticle's session plumbing. Direct tests pin all four verification polarities plus expiry.
