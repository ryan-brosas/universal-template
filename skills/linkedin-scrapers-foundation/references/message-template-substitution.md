<!-- capsule-v2 -->
# Message template substitution — how do I fill {{placeholders}} in outreach copy without breaking on emoji or missing values?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how does one shared substituter serve both connection-note templating and overlay-chat parsing, and why strip emoji before substitution?

## MessagesService.createMessage/_replace + generateMessage — mustache-lite regex loop over {label,value} pairs
**Path/Symbol:** `lib/helpers/messages.service.ts:MessagesService._replace` (:10–17), `.createMessage` (:39–53), `.messagesList` (:19–37); profile-side param mapper `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.generateMessage` (:432–447).
**Signature:** `_replace(content: string, name: string, value: string) -> string` (static); `createMessage(message: string, params: Array<{label, value}>) -> string`; `generateMessage(message, params: {firstName, lastName, companyName, profilePicture, myname?, mylastname?, mycompany?}) -> string`.
**Data Shape:** placeholders are double-curly `{{name}}`; values are emoji-stripped BEFORE insertion; `messagesList` returns `[{from: "Prospect"|"Me", message}]` by comparing each article's `<address>` text against the prospect name.

### Decisive source
```ts
// FAST-PATH GUARD — no "{{" anywhere ⇒ zero regex construction
static _replace(content: string, name: string, value: string) {
  if (content.indexOf('{{') === -1) {
    return content;
  }
  const reg = new RegExp(`\\{\\{${name}\\}\\}`, 'g');  // global: replace ALL occurrences
  return content.replace(reg, value);
}

async createMessage(message: string, params: MessageOptions[]) {
  for (let param of params) {
    message = MessagesService._replace(
      message,
      param.label,
      emojiStrip(param.value || ""),   // null/undefined value → "" not "undefined"
    );
  }
  return message.trim();
}

// abstract-service mapper — ONE call site wiring profile data to template labels
generateMessage(message, params) {
  return this.createMessage(message, [
    { label: "name",       value: capitalize(params.firstName) },
    { label: "last_name",  value: capitalize(params.lastName) },
    { label: "lastname",   value: capitalize(params.lastName) },
    { label: "myname",     value: capitalize(params.myname) },
    { label: "mylastname", value: capitalize(params.mylastname) },
    { label: "mycompany",  value: capitalize(params.mycompany) },
    { label: "company",    value: params.companyName },   // NOT capitalized
  ]);
}
```
**Flow:** template + ordered pairs → per pair: skip if no `{{` remains → build global regex from label → replace all occurrences with emoji-stripped value → trim result. The connect service feeds it via `generateMessage(message, {...info, ...data.extra})` so caller-supplied overrides win the spread. `messagesList` (:19–37) is the overlay-conversation twin used by Sales Nav chat flows — same file, attribution rule: `<address>` contains prospect name ⇒ `"Prospect"` else `"Me"`.
**Invariant:** values are sanitized (emoji-strip) BEFORE regex insertion — LinkedIn message inputs reject some emoji and stripped values also keep templates length-predictable; a MISSING pair leaves its literal `{{label}}` in place (no silent deletion), which makes unfilled templates visible in QA instead of sending half-identities; unknown keys never throw. Note `{{company}}` is deliberately NOT capitalized while person names are.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchors resolve uniquely (`MessagesService.createMessage` :39–53, `messagesList` :19–37).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "createMessage replace emojiStrip generateMessage placeholder", limit: 5 });
```

## Verdict
Adopt the fast-path-guarded global-replace loop with pre-insert sanitization and visible-unfilled-placeholder semantics; adapt the label set (add/remove per campaign fields) and swap `capitalize` behavior per locale; omit `messagesList`'s DOM attribution when an API transcript source exists (voyager clients should parse JSON instead). Contrast: Auto_job_applier config validation validates INPUTS before runs; this sanitizes VALUES at composition time — both prevent bad data reaching LinkedIn's UI layer, at different stages.
