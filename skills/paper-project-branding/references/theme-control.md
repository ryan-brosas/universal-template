# Theme Control lane

A control lane is a token-bound reference page plus an agent procedure. Paper's Theme panel owns editable token values. Canvas swatches, labels, and command examples are not clickable settings or dynamic text readouts.

## Setup on a template

Require explicit authorization to modify the reusable template. Confirm file/page identities and look for an existing Theme Control page before creating one. Preserve existing pages and appearance. Do not apply project branding during setup.

Read the existing source-variable-ID mapping, Figma aliases and modes, live Paper tokens, and current bindings. Reconcile captured source with live data rather than replaying an old import. Use the same canonical tokens; do not make a control-lane namespace.

Create or update two bounded sections:

- **Token console:** project palette owners, semantic surfaces/text, display/body typography, control/panel radii, and spacing specimens. Show exact token names and explain which entries are owners versus aliases. Bind previews to those entries. Preserve status palettes and local typography roles. Do not invent a universal density or mode switch when the system exposes several independent variables.
- **Component previews:** copy actual existing specimens with native descendant mappings. Include button, field, navigation, and modal where available. Preserve content/state/assets; change placement only. Copies share file tokens where bound, not linked component structure.

Label coverage honestly: connected properties, intentional literals, unsupported features, unaudited variants, and visual checks pending. A connected swatch does not certify a component family.

For detached properties, verify source-instance identity and aliases. Reuse the project's binding helper to reconnect a representative copy without changing resolved appearance. After checking it, apply the same property repair to the corresponding owner and explicitly matching targets. Do not silently broaden into an all-page repair.

## Operate by command

Interpret commands as token changes, not node repainting:

- **Apply a palette:** map approved palette steps to project-owner tokens. Preserve semantic alias relationships and independent success/danger colors. One primary value does not generate an accessible palette automatically.
- **Change typography:** resolve the display/body owner and verify fonts and layout; preserve explicit special families.
- **Change rounding or spacing:** identify the affected size roles and consumer scope. Clarify an ambiguous global request before changing every radius or spacing token.
- **Audit connections:** inspect stored references and source semantics across the requested pages; report exact coverage. Do not infer ownership from matching colors.

Before mutation, capture fresh affected definitions and the destination identity. Inspect each token/style result and ignored properties. On reruns, preserve unrelated edits and reconcile conflicts with the last applied state. Duplication requires revalidating destination IDs and bindings; source IDs are not destinations.

## Evidence and recovery

Render the console and component previews at baseline. For propagation, use an approved change or a bounded temporary color and non-color probe with exact restoration in `finally`. File-wide token changes are not isolated canaries: disclose scope and preserve a fresh recovery snapshot. Never recolor unrelated files.

Check a direct consumer, an aliased consumer, and an actual component. Stored references and successful token edits alone are not visual propagation proof. After an ambiguous failure inspect mutation results, restore temporary values, and stop repeated screenshot attempts. Record partial status rather than certifying the whole template.

Keep file/page IDs, copy mappings, repair scope, current control names, and evidence in the project's existing design records. The skill stores the procedure, not project-specific palettes or canvas IDs.
