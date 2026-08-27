<!-- capsule-v2 -->
# Email Notification Button Algebra — magic-link buttons only for single-small-input forms, with recipient identity baked into every token

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When may an email let a reviewer answer with one click, and what must ride inside the signed link?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/channels/email/renderer.py` whole (:1-227) — `_find_single_input_primitive` (:76-86), `_buttons_for_form` (:89-153), `_review_url_for_recipient` (:47-73), `_payload_lines` (:156-165), `build_notification_email` (:168-227).
**Signature:** `_buttons_for_form(form: FormDefinition | None, *, task_id, recipient, public_url) -> list[ButtonSpec]` / `build_notification_email(*, to, task_id, task_title, task_payload, redact_payload, form, from_email, from_name, reply_to, public_url, handoff_exp_unix=None) -> EmailMessage`.
**Data Shape:** `ButtonSpec{label, url, style}` — Switch ⇒ two buttons (true_label primary / false_label danger); SingleSelect ≤4 options ⇒ one per option (first primary, rest neutral); anything else ⇒ [] ⇒ plain `/task?id=` link-out.

### Decisive source
Module law up front (:1-10): "If the form contains EXACTLY one primitive that's a `switch` or a small `single_select` (≤4 options) and no other input fields, we emit magic-link buttons for each value." The gate (:83-86):
```python
    inputs = [f for f in form.fields if getattr(f, "name", "")]
    if len(inputs) != 1:
        return None
    return inputs[0]
```
Attribution rides inside the token (:98-101):
```python
    """Build magic-link buttons ...
    `recipient` is baked into each token so the action route can
    stamp `completed_by_email` on the task. Without it, the audit
    log shows "—" for every email completion."""
```
Per-recipient review URL ladder (:62-73): `handoff_exp_unix is None or not recipient` ⇒ unsigned `/task?id=`; else signed `/api/auth/email-handoff?to&t&e&s` via `sign_handoff` — LAZY-imported "to avoid pulling the crypto path into modules that only need the renderer for tests / docs preview". Callers pass `task.timeout_at` so the link dies when the task does (:184-190 docstring).

**Flow:** notify → build_notification_email resolves review_url ladder → buttons ladder → payload lines ([] when redacted or empty; values truncated 300→297+"…") → notification_html + notification_text twins → EmailMessage tagged {task_id}. Layout fields (display_text/section/divider/image) carry no `name`, so they never count as inputs — display_text + switch still gets buttons.
**Invariant:** multi-input forms are dashboard-only BY DESIGN (test docstring: "dashboard-only for v1") — one click must map to exactly one unambiguous value; the plain-text alternate is first-class, mirroring every button as "Label: url"; the Open-task CTA ALWAYS renders (3 buttons total on a switch form) and takes brand-primary styling only when it has no competing primary.

**Probe:** `tests/email/test_renderer.py` whole (:1-220): switch×2 buttons + text parity :37-47; ≤4 select×3 :50-65; >5 select link-out :68-79; long-text-only link-out :85-89; multi-input link-out :92-104; display-text invisible :107-116; no-form link-out :119-121; always-CTA :127-142; primary-when-alone brand-chunk assertion :145-168; plain-text CTA :171-177; redact hides values :192-196; HTML escape :199-205; subject/tags :211-220.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "build_notification_email renderer html plain text notification assembly buttons", limit: 6 });
```
Live at pin: rank-1 `build_notification_email` −35.64 (:168-227); `notification_html` −26.95; `notification_text` −25.3; `_buttons_for_form` −24.23 (:89-153); its direct tests at ranks (switch −23.76, ≤4-select −22.81, escape −22.6, display-text −20.18).

## Verdict
Adopt the conservative click-to-answer gate (exactly-one-small-input), token-baked recipient attribution, deadline-bound signed review URLs with lazy crypto imports, and HTML+plain-text parity. Adapt thresholds/primitive kinds to your form registry. Omit the plain-text mirror only if your audience is provably HTML-only — screen readers and text clients are why it exists.
