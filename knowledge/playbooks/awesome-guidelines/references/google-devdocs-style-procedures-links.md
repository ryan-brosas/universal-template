<!-- capsule-v2 -->
# Procedures and links — are steps numbered correctly with descriptive cross-references?

**Source:** Google style §Procedures, §Lists, §Cross-references and linking. **Question:** Do procedures place context before action and do links stand alone as meaningful phrases?

## Procedure seam
**Path/Symbol:** numbered task docs, how-to guides, tutorials.
**Signature:** numbered steps; location before action; Optional: steps; sub-steps a/b/i.
**Data Shape:** single-step → one bullet sentence.

### Decisive pattern
```
To create an instance, follow these steps:

1. In the Google Cloud console, go to the **VM instances** page.
2. Click **Create instance**.
3. Optional: Enable deletion protection.
```

**Flow:** introduce procedures with context sentence (colon if list follows immediately) → use **numbered lists** for sequences; **bulleted** for non-sequential sets; **description lists** for term/definition pairs → single-step tasks: one bullet sentence, not "1." → put **location/context before action** (In the console, click…) → state goal before action when helpful (To X, click…) → combine small sequential UI picks with `>` in one step (File > New) → sub-steps use lowercase letters / roman numerals → mark optional steps with `Optional:` at step start — not (Optional) → avoid please, keyboard shortcuts, directional above/below → don't repeat full procedures — link or reference earlier → focus command on what it does, not "run the following command" → put conditions **before** instructions.
**Invariant:** action-before-location, (Optional), or numbered one-step procedure fails Google procedure review.
**Probe:** step order audit; Optional: format check; intro sentence completeness.

## Link seam
**Flow:** link text = page title or descriptive phrase meaningful out of context → introduce with **For more information, see…** or **For more information about…, see…** (use about when purpose unclear; not "on") → avoid click here, this document, bare URLs → punctuation outside link → default same-tab; explain download/new-tab/same-page jumps → minimize duplicate links to same destination → provide brief context on page when possible instead of linking away for a sentence of info.
**Invariant:** vague link text or linked trailing punctuation fails cross-reference review.
**Probe:** link text out-of-context test; grep "click here|this document".

## Verdict
Numbered procedures with context-first steps, Optional: prefix, descriptive For more information links. Learning note: `google-devdocs-style-learning-note.md`.
