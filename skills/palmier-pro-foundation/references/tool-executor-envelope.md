<!-- capsule-v2 -->
# Tool executor envelope — what must wrap every tool call: gates, read fencing, diff publication, telemetry?

**Source:** PalmierPro GPL-3.0 `main@49841f35b3eafa65c7eadc7b168bcc74db632906`; Codebase Memory `palmier-pro`. **Question:** What ordering of validation, concurrency fencing, and change publication makes ~50 editor-mutating tools safe behind one entry point?

## executeWithOrigin
**Path/Symbol:** `Sources/PalmierPro/Agent/Tools/ToolExecutor.swift:ToolExecutor.executeWithOrigin` (92–225), dispatch `run` (320–376), `execute` wrapper (76–86).
**Signature:** `private func executeWithOrigin(name: String, args: [String: Any], origin: Analytics.Origin) async -> ToolResult`.
**Data Shape:** in: raw name + `[String: Any]` args + origin ("agent" | "mcp"); out: `ToolResult { content: [Block], isError }`; fencing tokens are opaque read revisions.

### Decisive source
```swift
guard let tool = ToolName(rawValue: name),
      origin.source != "mcp"
        || ToolDefinitions.mcpServer.contains(where: { $0.name == tool }) else {
    ... return ToolResult.error("Unknown tool: \(name)")   // MCP origin is allow-listed
}
...
let activeTimelineIdBefore = editor.activeTimelineId
let nonAgentMutationRevisionBefore = editor.nonAgentTimelineMutationRevision
let before = editor.timelines
let idsBefore = currentIdUniverse(editor)
do {
    let resolved = try expandingIdPrefixes(in: args, editor: editor)
    readRevision = editor.beginAgentTimelineRead(
        timelineReadActivity(for: tool, args: resolved, editor: editor))
    result = try await run(tool, editor, resolved)
} catch let err as ToolError { result = .error(err.message) }
catch { result = .error(error.localizedDescription) }
if let readRevision { editor.endAgentTimelineRead(readRevision, succeeded: !result.isError) }
...
if !result.isError, timelineChanged, tool.publishesTimelineChanges,
   editor.nonAgentTimelineMutationRevision == nonAgentMutationRevisionBefore,
   editor.activeTimelineId == activeTimelineIdBefore, ... {
    publishAgentChanges(before: previousTimeline, after: editor.timeline, editor: editor)
}
...
// Shorten on pre ∪ post ids: new ids and just-removed ids both stay short.
return await shorteningIds(in: result, editor: editor, alsoKnown: idsBefore)
```

**Flow:** scrub autofilled blanks → name+origin gate → MCP session activation hook → project-scoped tools short-circuit before editor exists → inactive-project guard (`projectFocusError`, failure reason `project_inactive`) → editor guard (`editor_unavailable`) → snapshot pre-state (timelines, active id, mutation revision, id universe) → expand id prefixes → begin timeline read fence → dispatch switch → end fence with success flag → conditional diff publication → feedback record + analytics + structured log → shorten ids over pre ∪ post universe.
**Invariant:** every exit path returns a `ToolResult` (errors never throw to the caller); a tool's UI-visible diff is published only when the mutation happened without an interleaved non-agent edit and on the same active timeline; reads taken under the fence are invalidated if they failed.
**Probe:** `Tests/PalmierProTests/Agent/ToolExecutorTests.swift:91-96` (unknown tool → `isError` containing "Unknown tool"); `:98-117` (`autofilledBlankArgsAreTreatedAsOmitted` — blank strings/NSNull dropped so lookups fail with "Provide either clipId", not "not found").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "palmier-pro", function_name: "executeWithOrigin", direction: "inbound", depth: 2 });
```

## Verdict
Adopt the envelope order (gate → guards → pre-snapshot → fence → dispatch → post-snapshot → conditional publish → telemetry) and typed failure reasons for analytics. Adapt the fencing primitives to your state container — PalmierPro's live on `EditorViewModel`; their writer side is uncited (next-pass target). Omit the specific tool switch. Coverage: ToolExecutor.swift `no_recorded_issue` @ gen 2026-08-25T19:59:55Z; tests read directly.
