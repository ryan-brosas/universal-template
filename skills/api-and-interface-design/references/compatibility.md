# Compatibility and evolution

Compatibility is a promise to particular consumers, not "never change anything."
Start with deployment independence, upgrade cadence, generated clients, stored
messages, and the project's release policy.

| Situation | Consider |
| --- | --- |
| Internal callers deployed together | Coordinated changes may need no explicit API version. Verify all callers and rollback behavior. |
| Independently deployed HTTP clients | An explicit version, additive evolution, or negotiated capability may help. Choose path, header, media type, or query placement from the existing protocol and infrastructure. |
| GraphQL | Schema evolution and deprecation are common; test consumer operations rather than adding URL versions by default. |
| Published SDK/library | Follow package-version and compatibility promises, including exports, runtime behavior, and dependency exposure. |
| Persisted events/documents | Plan readers, writers, migrations, mixed versions, and recovery separately from endpoint versions. |

Assess semantics as well as shape. "Additive" changes can still break strict
parsers, exhaustive enum handling, ordering assumptions, latency budgets, or retry
behavior. Tightened validation can reject inputs previously accepted. A version
label alone does not make those changes safe.

For a real break, choose a coordinated rollout or a supported overlap period,
communicate migration steps, and verify rollback where promised. Deprecation
windows and codemods earn their cost through consumer needs; do not require them
for an internal change with no compatibility commitment. For migration execution,
select `../../deprecation-and-migration/SKILL.md`.
