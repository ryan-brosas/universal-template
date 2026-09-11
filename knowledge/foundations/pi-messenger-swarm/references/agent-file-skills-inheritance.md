<!-- capsule-v2 -->
# Agent-file loader & skills inheritance — how do spawned subagents get custom personas AND the parent's skills?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How does `--agent-file` define an agent, and which child CLI args make it operational?

## Frontmatter-or-whole-file definition + discovered --skill flags
**Path/Symbol:** `swarm/agent-loader.ts:loadAgentDefinition` (:26-49), `swarm/spawn.ts:discoverSkills` (:272-296), `swarm/spawn.ts:createArgs` (:298-328).
**Signature:** `loadAgentDefinition(filePath): AgentDefinition { role, persona?, model?, objective?, systemPrompt }`.
**Data Shape:** frontmatter keys parsed line-wise (`key: value`, quotes stripped; NO nested YAML except the writer-side multiline `formatYamlMultiline :127-136`); body = system prompt.

### Decisive source
```ts
// No frontmatter - use whole file as system prompt, defaults for rest
return { role: 'Subagent', systemPrompt: content.trim() };
```
```ts
// Inherit non-extension skills so spawned agents can use cdp, zele, etc.
for (const skillPath of discoverSkills(state.cwd)) {
  args.push('--skill', skillPath);
}
...
fs.writeFileSync(promptPath, state.systemPrompt, { mode: 0o600 });
args.push('--append-system-prompt', promptPath);
```

**Flow:** spawn with `--agent-file` loads the def, APPENDS buildSwarmProtocol() to its body, prefers request.message over def.objective, inherits persona only when the request lacks one, and uses the FILE's model unless overridden. discoverSkills walks `<agentDir>/skills/*/SKILL.md` then `<cwd>/.pi/skills/*/SKILL.md`, passing each DIR as `--skill`. System prompt rides a mkdtemp file chmod 0o600, cleaned up in both close and error handlers (`cleanupTmpDir`).
**Invariant:** parseSimpleYaml is deliberately line-based — multi-line values in agent files would truncate silently; the writer side avoids that with YAML block scalar `|` formatting, so reader and writer must stay a matched pair. Protocol-append happens for BOTH paths (hand-built and file-defined) making clause coverage unconditional.
**Probe:** direct tests `tests/swarm/agent-loader.test.ts::parses frontmatter and returns body as system prompt` (:25) and `::handles file without frontmatter` (:49), `tests/swarm/agent-file-smoke.test.ts::spawns from agent file via handler` (:92); `grep -c "withFileTypes" swarm/spawn.ts` (=1); `grep -n "mode: 0o600" swarm/spawn.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "loadAgentDefinition discoverSkills createArgs formatYamlMultiline", limit: 6 });
```

## Verdict
Adopt frontmatter-or-body agent definitions plus explicit skill-dir forwarding and tmpfile system prompts; adapt the host CLI flags (`--append-system-prompt`, `--skill`); replace the toy YAML parser with a real one if you need nesting — then update the writer to match.
