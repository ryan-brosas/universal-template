---
name: paper-component-consistency
description: "Use when a reusable component in Paper must be created, audited, instantiated, migrated, or synchronized across pages while preserving intentional variants and content."
invocation: manual
disable-model-invocation: true
---

# Paper Component Consistency

Use built work to remove repeated decisions. Form the smallest relevant context,
then choose efficient operations. A canonical owner defines shared rules;
consumers retain intentional variation. Unique elements need not become components.

## Find the owners

Confirm active file and scope. Resolve owners for composition, theme, code
API/behavior/accessibility, content, and placement. Prefer existing specimens,
code, tests, stories, and tokens over new documents. Isolate conflicting ownership
before changing it. A copied screen is usage evidence, not automatically canonical;
compare relevant examples when no established owner exists.

Keep a temporary map: semantic identity, owner, consumers, invariants,
variants/states/slots, unknown differences, recovery needs, and checks. Use an
existing project index if useful; load only relevant families. Revalidate cached
IDs, ancestry, and file scope against live data. No registry is required.

## Compose by reuse

Prefer a matching complete pattern, then an existing variant, then shared
primitives. Inspect anatomy once. Reuse nested buttons, badges, icons, and text
roles as well as page shells, navigation, content widths, heading/action regions,
forms, and section rhythm. Different page purposes need not have identical layouts.
Discover only current gaps, not a speculative library.

Identify editable slots, protected properties, variants, and content-fitting rules.
Different labels or icons do not automatically create new definitions. Use verified
native instances/overrides where available; otherwise duplicate and retain returned
descendant mappings. Copies may share theme bindings without structural linkage.
Check cross-file reuse separately; copied dependencies are not synchronized.

Keep owners unchanged during instantiation. Substitute content through verified
mappings, preserving icon lanes, row geometry, and state. Test long labels and
optional content against intended wrapping, truncation, or expansion. For exact
Figma transfer, preserve source behavior rather than inventing a fitting policy.
Reuse tested helpers where useful, not a new synchronization framework.

## Improve the shared cause

Choose audit, create, instantiate, synchronize, or migrate to match the request;
audits are read-only. Probe current capabilities when needed. Combine supported
native features with small fallbacks rather than an old all-or-nothing limitation.

Repeated restyling, near-duplicates, and broken bindings can reveal an owner-level
fix. Improve that owner deliberately, then propagate accepted changes. Batch
confirmed equivalent consumers through an explicit property allowlist; inspect
exceptions separately. Preserve content, variants, and unresolved overrides.
Exclude unrelated pages. A local variant is not automatically a system decision.

Capture recovery proportional to risk: old values for small edits; hierarchy,
parent/order, content/state, JSX, renders, and consumers for subtree replacement.
Verify replacements before deleting originals; obtain confirmation before
destructive user-data changes. Inspect after ambiguous failures before retrying.

## Verify and leave useful context

Check anatomy, bindings, content, variants, and fresh renders. In an authorized
change or disposable fixture, observe theme propagation separately from owner
layout/anatomy propagation. A deep copy is not proof of linked-instance behavior.
Exercise relevant content, states, modes, and widths; resizing a frame alone is not
responsive proof. Canvas previews do not establish code interaction or accessibility.

A pending specimen may enter a labeled reuse pilot, but successful composition
does not certify Figma fidelity. Report unverified scope. Persist only context
that saves repeated discovery or coordination in existing project owners, examples,
or a short note. Product tokens, source links, and decisions stay in the project.
Report owners, reused work, consumers, intentional differences, and actual checks.
Judge benefit by avoided rediscovery and repeated edits, not library size.

## Focused references

- `references/reuse-first.md`: clone maps, slot fitting, and recovery receipts.
- `references/paper-specifics.md`: connection recovery and operation caveats.
- `../pencil/references/tokens.md`: theme ownership, bindings, modes, and scope.
- `../pencil/SKILL.md`: literal transfer; `../pixel-perfect/SKILL.md`: fidelity diagnosis.
- `../prototype/SKILL.md`: exploration before shared rules are established.
