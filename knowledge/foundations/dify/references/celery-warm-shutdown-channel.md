<!-- capsule-v2 -->
# celery-warm-shutdown-channel — How does a worker shutdown become a workflow abort?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do you merge process-local signals with distributed commands into one abort stream?

## Combined channel: fan-in fetch, primary-only send, one-shot signal translation
**Path/Symbol:** `api/core/app/apps/workflow/command_channels.py:CombinedCommandChannel` (:15-36), `CelerySignalCommandChannel` (:40-67); wired in `api/core/app/apps/workflow/app_runner.py:run` (:156-167).
**Signature:** `CombinedCommandChannel(channels: Sequence[CommandChannel])`; `CelerySignalCommandChannel(*, shutdown_state_getter: Callable[[], bool], abort_reason: str)`.
**Data Shape:** Tuple of channels; `fetch_commands()` returns merged `list[GraphEngineCommand]`; the Celery channel emits exactly one `AbortCommand` per instance (latch `_abort_emitted`); `send_command` routes to `_command_channels[0]`.

### Decisive source
```python
@final
class CombinedCommandChannel:
    """Fetch commands from all sources and send outbound commands through the primary source."""
    def fetch_commands(self) -> list[GraphEngineCommand]:
        commands: list[GraphEngineCommand] = []
        for channel in self._command_channels:
            try:
                commands.extend(channel.fetch_commands())
            except Exception:
                logger.exception("Failed to fetch GraphEngine commands from %s", channel.__class__.__name__)
        return commands

    def send_command(self, command: GraphEngineCommand) -> None:
        self._command_channels[0].send_command(command)

@final
class CelerySignalCommandChannel(CommandChannel):
    """Translate process-local Celery shutdown state into one GraphEngine abort command."""
    def fetch_commands(self) -> list[GraphEngineCommand]:
        if self._abort_emitted or not self._shutdown_state_getter():
            return []
        self._abort_emitted = True
        return [AbortCommand(reason=self._abort_reason)]
```

**Flow:** engine polls the combined channel each tick → Redis commands and the warm-shutdown latch both drain into one list → a failing source is logged-and-skipped so one broken channel cannot hide commands from healthy ones → when Celery marks warm-shutdown, the NEXT poll yields exactly one AbortCommand(WORKFLOW_WARM_SHUTDOWN_ABORT_REASON), then never again.
**Invariant:** Fetch failures are isolated per-channel (never raise out of fetch); sends go to exactly ONE sink — there is no broadcast; the shutdown translation is once-per-channel-instance, not once-per-process, because each running workflow builds its own channel pair.
**Probe:** `grep -c '_abort_emitted' core/app/apps/workflow/command_channels.py` → 4; `grep -cF 'self._command_channels[0].send_command' …` → 1; direct tests `tests/unit_tests/core/app/apps/workflow/test_command_channels.py::test_combined_command_channel_continues_after_source_failure`, `::test_celery_signal_command_channel_emits_abort_once_per_instance`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "CombinedCommandChannel CelerySignalCommandChannel fetch commands", limit: 10 });
```

## Verdict
Adopt the fan-in/primary-send split and the one-shot getter-to-command adapter. Adapt what the second "channel" listens to (SIGTERM handlers, K8s preStop files, config reloads). Omit the Celery-specific naming.
