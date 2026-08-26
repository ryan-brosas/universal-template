<!-- capsule-v2 -->
# Prompt tools→permission projection — how does the deprecated per-prompt tools map become session permission rules?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How are `{bash:false, read:true}` style prompt options converted to enforceable rules — and what happens on the NEXT prompt without them?

## Whole-map REPLACE semantics
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (`prompt`, lines 1052–1071).
**Signature:** `prompt(input): Effect<WithParts, Image.Error>` — projection block :1060–1067.
**Data Shape:** `input.tools?: Record<string, boolean>` (schema-annotated `@deprecated` — merged into permissions). Each entry becomes `{permission: <toolName>, action: enabled ? "allow" : "deny", pattern: "*"}`; non-empty map ⇒ REPLACES `session.permission` wholesale via `sessions.setPermission`; empty/absent ⇒ prior rules persist. `noReply: true` short-circuits after message creation (no loop).
**Decisive source:**
```ts
// prompt.ts:1060-1069
const permissions: PermissionV1.Rule[] = []
for (const [t, enabled] of Object.entries(input.tools ?? {})) {
  permissions.push({ permission: t, action: enabled ? "allow" : "deny", pattern: "*" })
}
if (permissions.length > 0) {
  session.permission = permissions                       // in-memory AND...
  yield* sessions.setPermission({ sessionID: session.id, permission: permissions }) // persisted
}
if (input.noReply === true) return message
return yield* loop({ sessionID: input.sessionID })
```

**Flow:** createUserMessage (agent/model persistence + part resolution) → touch → project tools map → maybe run loop. Downstream, SessionTools.resolve and subtask asks merge these session rules with agent rules (`Permission.merge(taskAgent.permission, session.permission ?? [])`), so a prompt-level deny wins for that session until replaced.
**Invariant:** The map is a FULL SPECIFICATION, not a patch: sending `{read:true}` after `{bash:false}` leaves bash back at its default ("ask") because the new array replaces the old — pinned explicitly by test. A porter who MERGES maps instead of replacing turns temporary denies permanent.
**Probe:** `packages/opencode/test/session/prompt.test.ts:991` "prompt tools replace previous prompt tool rules" — second prompt with `{read:true}` yields exactly `[{permission:"read",pattern:"*",action:"allow"}]` and `Permission.evaluate("bash",…)` returns "ask".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", qn_pattern: "packages.opencode.src.session.prompt", limit: 20, detail: "ids" });
```

## Verdict
Adopt replace-not-merge projection with wildcard patterns and noReply short-circuit; adapt rule schema names; omit deprecation messaging.
