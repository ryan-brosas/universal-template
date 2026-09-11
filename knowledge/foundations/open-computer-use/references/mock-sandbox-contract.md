<!-- capsule-v2 -->
# Mock-sandbox test harness — how is the whole agent exercised without E2B or live models?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** What does the repo's own direct test pin about SandboxAgent's sandbox contract?

## tests/sandbox_agent.py MockSandbox: the de-facto interface spec
**Path/Symbol:** `tests/sandbox_agent.py:5-23` (`MockSandbox`), `:26-34` (main harness).
**Signature:** mock implements exactly: `screenshot() -> bytes`, `commands.run(command, timeout, background) -> {stdout, stderr}`, `set_timeout(timeout)`, plus attribute wiring `self.commands = self`.
**Data Shape:** Static PNG from `./tests/test_screenshot.png` returned as raw bytes (the same bytes-in-content convention the LLM layer wraps); run() returns a stub object carrying stdout/stderr strings only.

### Decisive source
```python
class MockSandbox:
    def __init__(self):
        self.timeout = 60
        self.commands = self          # namespace collapse: commands.run IS self.run

    def screenshot(self):
        with open("./tests/test_screenshot.png", "rb") as f:
            return f.read()

    def run(self, command, timeout=None, background=False):
        class MockResult:
            def __init__(self):
                self.stdout = f"Mock stdout for command: {command}"
                self.stderr = ""
        return MockResult()

    def set_timeout(self, timeout):
        self.timeout = timeout
```

**Flow:** instantiate `SandboxAgent(MockSandbox(), save_logs=False)` → run("Open the Firefox browser") → the full thought→action loop executes against static bytes; only the MODEL providers stay live (this harness verifies providers work; it is not an offline unit test).
**Invariant:** The minimal portability surface of "a sandbox" here is FOUR verbs — screenshot bytes, synchronous command w/ timeout+background, background start, keep-alive set_timeout — plus mouse/press/write used by the tool methods (unmocked because the sample instruction never clicks). Any replacement runtime (Docker, local X, another cloud) must satisfy this surface. `self.commands = self` shows the commands namespace is a facade, not a required sub-object.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && sed -n '5,23p' tests/sandbox_agent.py` (verbatim contract); note `save_logs=False` proves Logger works without log_file.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "MockSandbox screenshot set_timeout commands run", limit: 6, fields: ["signature", "name", "file"] });
// expect tests/sandbox_agent.py MockSandbox nodes
```

## Verdict
Adopt MockSandbox as the porting acceptance fixture — reimplement these four verbs and the agent core runs anywhere; adapt by extending mocks for mouse/keyboard when testing click paths; omit nothing (the whole file is load-bearing contract).
