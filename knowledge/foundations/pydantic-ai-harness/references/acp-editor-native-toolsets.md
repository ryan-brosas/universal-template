<!-- capsule-v2 -->
# ACP editor-native toolsets — how do agent fs/shell tools run inside the editor instead of the agent host, safely?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** How can an agent's `read_file`/`write_file`/`run_command` tools be backed by the CLIENT's filesystem and terminal (seeing unsaved buffers, running in the editor's env), what must happen when the client advertises only partial capability, and how does a cancelled command still kill a terminal whose create-response may arrive after cancellation?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_client_toolsets.py` — `AcpFileSystemToolset` (:47–99, `_absolute` :76–80, `read_file`/`write_file` :82–99), factory `acp_filesystem` (:102–135), `_LocalFileWriter` protocol (:41–44), `AcpTerminalToolset.run_command` (:151–216), factory `acp_terminal` (:219–238).

**Signature:**
```python
class AcpFileSystemToolset(FunctionToolset[AgentDepsT]):
    def __init__(self, *, client: Client, session_id: str, cwd: str | None = None,
                 local_writer: _LocalFileWriter | None = None) -> None
def acp_filesystem(session: AcpSession) -> AcpFileSystemToolset[None] | None
async def run_command(self, command: str) -> str
```

**Data Shape:** Tools named exactly like the local `FileSystem`/`Shell` capabilities (`read_file`, `write_file`, `run_command`) so the default presenter renders them identically. `acp_filesystem` returns a toolset when the client advertised `fs/read_text_file`; `local_writer` is set only when `fs/write_text_file` is NOT advertised (reads via editor, writes to a local `FileSystem(root_dir=session.cwd)`); returns `None` only with no readable fs so callers fall back to a fully local toolset.

### Decisive source
Path rooting + honest boundary (:71–75): "ACP requires absolute paths, but models routinely produce workspace-relative ones ... relative paths are resolved against it before reaching the wire. The client still resolves and authorizes every path itself (this toolset adds no sandboxing of its own)." Terminal cancel choreography (:191–216):
```python
        # The create runs as its own task so a cancellation landing mid-flight cannot abandon the
        # request: it may already be on the wire ..., so its response must still be read to learn
        # the id and clean up. A raw `task.cancel()` ... pierces anyio shields, so the create must
        # live outside this task; `asyncio.wait` rather than `asyncio.shield` because shield on
        # 3.12+ reports a late create failure to the loop exception handler even when the cleanup
        # below retrieves it.
        create = asyncio.ensure_future(self._client.create_terminal(...))
        ...
        except asyncio.CancelledError:
            with anyio.CancelScope(shield=True):
                if terminal_id is None:
                    with contextlib.suppress(Exception):
                        terminal_id = (await create).terminal_id
                if terminal_id is not None:
                    with contextlib.suppress(Exception):
                        await self._client.kill_terminal(...)
            raise
        finally:
            if terminal_id is not None:
                with anyio.CancelScope(shield=True), contextlib.suppress(Exception):
                    await self._client.release_terminal(...)
```

**Flow:** session config time → factories inspect `session.client_capabilities` → toolset wired into `AcpSessionConfig.toolsets`. read_file/write_file → `_absolute(cwd-relative→absolute)` → client RPC (`fs/read_text_file`/`fs/write_text_file`) or `_LocalFileWriter`. run_command → ensure_future(create) → wait exit → read output → format; cancel at ANY stage: shielded kill (learning the id from the still-running create if needed) then always release; suppressed client errors never replace the CancelledError the caller needs.

**Invariant:** The editor stays the authority for path authorization (the adapter adds routing, not sandboxing). Capability advertisement gates each route; the read-only-client fallback writes locally ONLY when agent and editor share the workspace disk (documented remote-editor caveat). Every terminal that came into existence is killed on cancel and released always; cleanup failures are suppressed so they cannot mask the in-flight outcome.

**Probe:** `bash -c 'cd $REFERENCE_ROOT/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest tests/experimental/acp/test_client_toolsets.py "tests/experimental/acp/test_acp.py::TestCancellation::test_cancel_during_terminal_create_kills_the_terminal_end_to_end" -q'` — terminal killed+released on cancel incl. failing-kill survival; end-to-end late-create race leaves `killed == ['term-1']` and `released == ['term-1']`. (Executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "AcpTerminalToolset create_terminal kill_terminal release_terminal cancellation", limit: 5 });
```
Observed live: rank#1 `test_run_command_kills_and_releases_the_terminal_on_cancel` (tests/experimental/acp/test_client_toolsets.py :188–196); `AcpTerminalToolset` (_client_toolsets.py :151–216) adjacent; `acp_filesystem` factory (:102–135).

## Verdict
**Adopt** client-backed tool routing gated by advertised capabilities with a per-route local fallback and the shared-disk caveat spelled out. **Adopt** name-matching against your local tools so presentation/reuse stay uniform. **Adopt** the ensure_future + asyncio.wait + shielded-cleanup pattern for any cancellable request whose response you need during unwind (id-learning cleanup). **Omit** the sandboxing expectation — this plane deliberately delegates authorization to the editor. Caveat: none — dedicated suite plus an end-to-end cancel race test pin it at this pin.
