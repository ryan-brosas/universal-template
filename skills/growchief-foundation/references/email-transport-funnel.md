<!-- capsule-v2 -->
# Email transport funnel — how do transactional emails choose a provider, and why does one path go through a durable singleton while the other goes direct?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** notifications and exports both send mail — how do you get burst-safe sending without duplicating provider plumbing?

## Env-selected provider behind one interface; async path funnels through the 'send-emails' singleton, sync path calls direct
**Path/Symbol:** `shared/server/email/email.service.ts:EmailService` (:9-137); boot registration `shared/server/temporal/temporal.client.subscription.register.ts:onModuleInit` (:8-19); provider contract `shared/server/email/email.interface.ts:EmailInterface` (:1-13).
**Signature:** `selectProvider(provider: string): EmailInterface`; `sendEmail(to, subject, html, replyTo?, buffer?)` → `signalWorkflow('send-emails', 'email', [{...}])`; `sendEmailSync(...)` → direct provider call after HTML template wrap.
**Data Shape:** provider contract = `{ name: string; validateEnvKeys: string[]; sendEmail(to, subject, html, emailFromName, emailFromAddress, replyTo?, buffer?): Promise<any> }`. Singleton workflowId literal `'send-emails'`, signal name `'email'`.

### Decisive source
```ts
constructor() {
  this.emailService = this.selectProvider(process.env.EMAIL_PROVIDER!);
  for (const key of this.emailService.validateEnvKeys)
    if (!process.env[key]) console.error('Missing environment variable: ' + key);
}
async sendEmail(to, subject, html, replyTo?, buffer?) {
  if (to.indexOf('@') === -1) return;                    // fail-soft guard 1
  if (!process.env.EMAIL_FROM_ADDRESS || !process.env.EMAIL_FROM_NAME) return; // guard 2
  await this._temporalService.signalWorkflow('send-emails', 'email',
    [{ to, subject, html, replyTo, buffer }]);
}
hasProvider() { return !(this.emailService instanceof EmptyProvider); }
```

**Flow:** construction picks ONE provider (resend | nodemailer | default EmptyProvider) and logs missing env keys at boot; ASYNC path validates then forwards payloads into the durable `send-emails` singleton (started at boot IFF `EMAIL_PROVIDER` set, swallow-catch idempotent), which queues and drains them through the `sendEmailSync` ACTIVITY → back into `EmailService.sendEmailSync` → provider; SYNC path skips the funnel, wraps html in a branded card template, and calls the provider inline. The singleton body (workflow.email.ts:24-43) is the same mutex-queue + drained-condition shape as the other singletons.
**Invariant:** BOTH paths share identical fail-soft guards (no `@` in `to` ⇒ silent return; missing sender env ⇒ log + return) — email problems NEVER throw into business flows; the funnel exists so bursts (per-lead exports, notification storms) drain through one durable queue instead of unbounded parallel HTTP sends.
**Provider deltas worth porting:** Resend spreads attachments conditionally (`...(buffer && { attachments: [{ content: buffer, filename: 'recording.zip', contentType: 'application/zip' }] })`) and maps `replyTo`→`reply_to`; NodeMailer duplicates html into `text` (plain-text fallback = raw HTML source).
**Probe:** no upstream tests exist. Deterministic pins (executed): `grep -n "instanceof EmptyProvider\|case 'resend'\|case 'nodemailer'\|signalWorkflow('send-emails'" shared/server/email/email.service.ts` → :22/:27/:29/:53; registration pins → :15 (+'subscription-deactivate' :26).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "sendEmailSync selectProvider EmptyProvider", limit: 6 });
```

## Verdict
Adopt: one provider interface selected once at boot with an explicit EMPTY default + hasProvider() feature gate, dual-path dispatch (durable funnel for bursts, direct for interactive), identical fail-soft guards on both. Adapt the durable layer to your scheduler; rename 'recording.zip'. Omit the inline CSS brand template. Caveat: pattern-twin overlap with already-mined singleton queue shapes is acknowledged — THIS capsule claims only the transport-funnel contract and provider-selection policy.
