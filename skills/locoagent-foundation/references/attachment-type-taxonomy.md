<!-- capsule-v2 -->
# Attachment type taxonomy — what is the full message space of dynamic model-facing context, and how does a new kind slot in?

**Source:** locoagent (Claude Code CLI fork, license: proprietary upstream, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the discriminated-union vocabulary every collector emits and renders.

## Attachment union
**Path/Symbol:** `src/utils/attachments.ts:Attachment` (:440-717) plus named members `FileAttachment` (:295-305), `CompactFileReferenceAttachment` (:307-312), `PDFReferenceAttachment` (:314-321), `AlreadyReadFileAttachment` (:323-333), `TeammateMailboxAttachment` (:719-728), `TeamContextAttachment` (:730-737), `HookAttachment` family (:352-438).
**Signature:** ~45-member tagged union discriminated on literal `type`.
**Data Shape:** every filesystem-bearing member carries `displayPath` computed as `relative(getCwd(), path)` AT CREATION TIME ("for stable display") — never re-derived at render.

### Decisive source
```ts
| {
    type: 'relevant_memories'
    memories: {
      path: string; content: string; mtimeMs: number
      /**
       * Pre-computed header string (age + path prefix).  Computed once
       * at attachment-creation time so the rendered bytes are stable
       * across turns — recomputing memoryAge(mtimeMs) at render time
       * calls Date.now(), so "saved 3 days ago" becomes "saved 4 days
       * ago" across turns → different bytes → prompt cache bust.
       */
      header?: string
      /** Threaded to the readFileState write so getChangedFiles skips
       *  truncated memories (partial content would yield a misleading diff). */
      limit?: number
    }[]
  }
```

**Flow:** collectors construct typed members → `createAttachmentMessage` (:3201-3210) wraps each in `{ attachment, type: 'attachment', uuid, timestamp }` → the renderer switches on `attachment.type`. Families present: file content (file / already_read_file / compact_file_reference / pdf_reference / edited_*_file / directory), memory (nested_memory / relevant_memories / current_session_memory), skills (dynamic_skill / skill_listing / skill_discovery / invoked_skills), interaction (queued_command / agent_mention / ide selections), modes (plan_mode{,_reentry,_exit} / auto_mode{,_exit} / verify_plan_reminder), economy (token_usage / budget_usd / output_token_usage), swarm (teammate_mailbox / team_context / teammate_shutdown_batch), hygiene (todo_reminder / task_reminder / task_status / diagnostics / deferred_tools_delta / agent_listing_delta / mcp_instructions_delta / date_change / compaction_reminder / max_turns_reached).
**Invariant:** anything rendered into the transcript must be byte-stable across turns — derive all volatile text (ages, dates, listings) once at creation, store it on the attachment, and fall back gracefully for resumed sessions that predate the field (`header?` optional + render-path recompute fallback). New members join the union + renderer switch; nothing else may smuggle dynamic text.
**Probe:** no upstream test pins the union (coverage caveat). Deterministic probe: `grep -c "type: '" src/utils/attachments.ts` ≈ 45 member literals; the header rationale comment is pinned verbatim at :505-514.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "Attachment union relevant_memories queued_command plan_mode", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the tagged-union message space, creation-time `displayPath`, and the precomputed-volatile-text-for-cache-stability rule; adapt member set to your host's features; omit Anthropic-specific types you have no renderer for. Porting trap: recomputing human-readable ages at render time silently busts the prompt cache every turn boundary the text crosses.
