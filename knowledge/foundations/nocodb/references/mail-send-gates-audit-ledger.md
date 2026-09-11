<!-- capsule-v2 -->
# Mail send gates & audit ledger — when must an email NOT be sent, and how is every attempt recorded without lying about it?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** What stands between a caller and the SMTP adapter, and what does the send ledger record on success vs failure?

## Site-URL gate + once-only super-admin nag, then send-capture-ledger with privacy skips
**Path/Symbol:** `packages/nocodb/src/services/mail/mail.service.ts` — getAdapter (:28–38), notifySuperAdmin (:47–87), ensurePublicUrl (:89–99), resolveSubject (:117–138), dispatchAndLog (:161–214), buildUrl (:216–300), sendMail switch (:333–561).
**Signature:** `sendMail(params: {payload, mailEvent}): Promise<boolean>` — boolean contract, never throws; `dispatchAndLog(adapter, ncMeta, {event, fk_user_id?, to, subject, html})`.
**Data Shape:** ledger row nc_mail_sends {event, fk_user_id|null, to_email, subject, status 'sent'|'failed', error ≤8000 chars|null, sent_at Date|null}; cache flag `system:public_url_missing_notified` (root scope).

### Decisive source
```ts
// adapter-missing is CONFIG state, not an error: warn ONCE per process
if (!MailService.adapterMissingLogged) { MailService.adapterMissingLogged = true; logger.warn('Email Plugin not configured / active'); }
return null;

if (mailEvent !== MailEvent.FORM_SUBMISSION) {
  if (!(await this.ensurePublicUrl(ncMeta))) return false;   // NC_SITE_URL gate
}

status: sendError ? 'failed' : 'sent',
error: sendError ? String(sendError?.message ?? sendError).slice(0, 8000) : null,
sent_at: sendError ? null : new Date(),
// audit-row INSERT failures are logged but never re-thrown — the email is what matters
if (sendError) throw sendError;   // LAST line: outer catch keeps sendMail's boolean contract

// Events in SKIP_STORING_MAIL_EVENTS send but don't log (user-content paths)
```
(:32–37, :341–345, :198–213 condensed)

**Flow:** getAdapter (null ⇒ sendMail:false silently after one warn) → site-URL gate for link-bearing events (host header can be spoofed; emails need safe absolute URLs — first refusal also emails the super user found via `roles LIKE '%super%'`, gated by the once-per-install cache flag) → branding hooks (CE null stubs; EE overrides white-label From display name + productName) → per-event switch renders @react-email JSX templates and calls dispatchAndLog → adapter.mailSend with captured error → ledger row → conditional skip-set check BEFORE ledger write.
**Invariant:** sendMail NEVER throws (catch ⇒ log + return false) — callers gate UX on the boolean; the ledger records ATTEMPTS truthfully (sent_at null on failure, error truncated to 8000 chars) yet ledger-write failure never masks the send outcome; SKIP_STORING_MAIL_EVENTS exists because form-submission recipients/payloads are END-USER DATA (privacy split, not a bug); subject white-labeling goes ONLY through `(productName)=>string` builders — plain-string subjects are used VERBATIM because blind "NocoDB" string-replace would rebrand unintended occurrences (documented in-code doctrine); buildUrl ladder pins link shapes (token ⇒ /signup/<token> unless email-auth disabled; reset/verify tokens are BACKEND-served paths without dashboard prefix). Cross-ref: plugin-manager-lifecycle (why emailAdapter returns null while storage falls back to Local).
**Probe:** `grep -c "adapterMissingLogged" packages/nocodb/src/services/mail/mail.service.ts` (=3: decl + guard + set) · `grep -c "PUBLIC_URL_NOTIFIED_CACHE_KEY" packages/nocodb/src/services/mail/mail.service.ts` (=3: decl + get + set) · `grep -c "SKIP_STORING_MAIL_EVENTS" packages/nocodb/src/services/mail/mail.service.ts` (=4: import + docstring ×2 + gate) · `grep -c "slice(0, 8000)" packages/nocodb/src/services/mail/mail.service.ts` (=1) · `grep -c "%super%" packages/nocodb/src/services/mail/mail.service.ts` (=1) · `grep -c "FORM_SUBMISSION" packages/nocodb/src/services/mail/mail.service.ts` (=3: comment + exemption + case).
**Direct test:** none upstream for mail.service.ts — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "MailService dispatchAndLog ensurePublicUrl notifySuperAdmin renderMail", limit: 10 });
```

## Verdict
Adopt the three gates (adapter-config soft-null, safe-URL requirement, event allow-switch) and the truthful-attempt ledger with a privacy skip-set for any outbound comms plane; adapt the ledger schema and truncation bound to your storage; omit the super-admin nag if your host configures URLs out-of-band. Coverage caveat: grep-pinned only; full-file direct read performed (562 lines).
