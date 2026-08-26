# Foundation quality bar: graph-led, code-grounded shortcut utility

A foundation succeeds when another agent can retrieve and port proven code without rediscovering the repository. The memory graph selects a connected seam; source and direct tests establish the claim. A skill carries the retrieval decision, contract, decisive evidence, and behavioral boundary—not a repository summary.

## The failure pattern
A repo sweep, module census, or prose volume target is not evidence. They create generic summaries, invented taxonomies, stale copied code, and claims of completeness. Never score by length, count, citation count, or the amount of code copied in.

## The useful unit: an implementation capsule
A legacy `<!-- capsule-v1 -->` reference supplies retrieval metadata. Every new or substantively rewritten reference uses `<!-- capsule-v2 -->` and answers one porting question with:

- **Source** pinned to the inspected repository revision;
- **Path/Symbol**, **Signature**, **Data Shape**, **Flow**, and **Invariant**;
- a labelled **Decisive source** excerpt (or labelled pseudocode only when code is not the useful representation);
- a **Probe** naming a direct test path and its observable boundary; and
- a graph **Retrieve** call using `search_graph`.

The capsule contains only enough surrounding code to prevent the likely wrong port. It does not duplicate a module or convert memory-graph output into prose.

## Evidence hierarchy
1. Current source plus its direct test.
2. Fresh, covered graph symbols and high-confidence traces used to select the seam.
3. Source comments that explain a non-obvious trade-off.
4. Documentation/history for context.

The graph chooses what to inspect; source overrides it. If the direct test is excluded or absent, state that caveat rather than inventing coverage.

## Behavior pressure test
Score five bars: right graph seam, relevant primitive, exact retrieval target, preserved invariant/direct-test probe, and no irrelevant loading. RED exposes a specific retrieval miss; GREEN passes twice at 4/5, including an adversarial prompt. With no runner, record the block and use deterministic retrieval/probe checks; never fabricate a pass.

## Reference acceptance
Done when the porting question, pinned source, graph retrieval, decisive evidence, direct-test probe, invariant, verdict, and any coverage caveat are present. Removing non-load-bearing text is welcome. No repository-wide completion claim is permitted unless that scope was independently evidenced.
