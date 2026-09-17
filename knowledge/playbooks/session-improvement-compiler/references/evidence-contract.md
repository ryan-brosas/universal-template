# Evidence, explanation, and scope

## Establish what happened

Raw session events, actual tool output, supplied transcripts, user corrections,
and real changes establish the work performed. Current source, tests, requirements,
and runtime behavior establish what is true now. A historical success may no longer
apply after the implementation changes; retain both the result and its conditions.

History search, recall, or reflection services are optional locators and pattern
suggesters. Fabric, Hindsight, and other providers are not prerequisites, and their
summaries are not independent corroboration. Retrieve the smallest supporting
range. When the visible conversation lacks earlier work, distinguish uninspected
history from unavailable evidence. If an authorized transcript or history locator
is available, make a bounded check before asking the user to supply it. In
this template that bounded check is the project's Hindsight bank (`hindsight_recall`
for prior lessons, `hindsight_reflect` for a synthesized view) together with any
stored reflection records under `background/reflections/*` in the project's Fabric
mesh, which carry earlier sessions' findings, proposals and retained ids; cite the
overlapping ids and skip what they already establish. Use `hindsight_status` for
Hindsight readiness and check Fabric records separately. Unconfigured, unsynced or
empty providers are stated limitations, not reasons to invent provenance or to ask
the user for history the session already contains. Confirm session identity or an
explicit continuation link; the same repository or a recent timestamp does not
establish that another session's work belongs here. If no relevant evidence is
found, state what was checked and defer unsupported lessons.

A recalled summary is a pointer, not a name service: verify the identifiers it
returns against the working tree before repeating them. Observed 2026-09-17, a recall
of this template's own prompts named a file that does not exist
(`compile-session-skill` for the real `compile-skill`); the repository was
correct and the recall was not.
Do not require history access when supplied events suffice, or duplicate session
history in a permanent artifact.

## Explain the useful experience

For each meaningful candidate, consider naturally:

- What action, decision, correction, or sequence led to which observed outcome?
- Which evidence supports the explanation? What else could explain it?
- Was a success due to the technique, the input, environment, or constraints?
- What is demonstrated, what is plausible, and what would distinguish them?
- When could future work reuse the lesson? What boundaries or counterexamples matter?
- What owner could change the outcome, and what would show the change helped?

These are reasoning questions, not required fields, a schema, or a scoring rubric.
A temporary comparison can help complex work, but needs no durable learning ledger.
A successful recovery proves a usable recovery path under those conditions, not
necessarily the cause of the original failure. Keep useful observations even when
the causal explanation remains open; scope adoption to what was demonstrated.

## Retain experience, not an inventory

An answer to “where is this implemented?” normally belongs to source retrieval,
Sourcebot, GitHub, tests, docs, or Git history. A diagnostic order that eliminated
repeated investigation may be hard to recover from source alone. Preserve that
order and its decision points, not a repository summary.

One strong session may justify adoption: an expensive demonstrated failure, an
explicit durable correction, or a clearly useful method need not recur first.
Conversely, repeated preference does not establish a universal rule. A local
constraint remains local unless evidence supports broader applicability.

After understanding the lesson, use [owner selection](../../leverage-capture/README.md).
There is no priority order placing gates or skills ahead of code, configuration,
project ownership, or no change. Split a lesson only where distinct responsibilities
need distinct changes; keep a single source of truth for each.

## Privacy

Shared procedures retain the method and its conditions, not credentials, private
client details, raw transcripts, machine-specific IDs, or temporary file paths.
Use existing task/PR history for necessary evidence references. Do not save another
session summary merely to prove that reflection occurred.
