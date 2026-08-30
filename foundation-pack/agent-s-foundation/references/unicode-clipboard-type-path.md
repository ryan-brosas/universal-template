<!-- capsule-v2 -->
# unicode-clipboard-type-path — When must typing route through the clipboard instead of pyautogui.write?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What is the ASCII/Unicode split in the type action, and how is the clipboard dependency made self-healing?

## Type seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:OSWorldACI.type` (:413-463).
**Signature:** `type(element_description=None, text="", overwrite=False, enter=False) -> str` (an @agent_action returning an executable string).
**Data Shape:** Emitted command = optional focus click + optional select-all+backspace (overwrite) + text entry + optional Enter. Text entry arm chosen by `any(ord(char) > 127 for char in text)`.

### Decisive source
```python
# self-healing import preamble emitted INTO the action string
command += ("\ntry:\n"
    "    import pyperclip\n"
    "except ImportError:\n"
    "    import subprocess\n"
    '    subprocess.run(\'echo "osworld-public-evaluation" | sudo -S apt-get install -y xclip xsel\', shell=True, check=True)\n'
    "    subprocess.check_call([subprocess.sys.executable, '-m', 'pip', 'install', 'pyperclip'])\n"
    "    import pyperclip\n\n")

has_unicode = any(ord(char) > 127 for char in text)
if has_unicode:
    command += f"pyperclip.copy({repr(text)}); "
    command += f"pyautogui.hotkey({repr('command' if self.platform == 'darwin' else 'ctrl')}, 'v'); "
else:
    command += f"pyautogui.write({repr(text)}); "
```

**Flow:** element_description given ⇒ ground + click first → overwrite ⇒ platform-correct select-all ('command' on darwin else 'ctrl') + backspace → Unicode detected ⇒ copy to clipboard + paste hotkey; ASCII ⇒ pyautogui.write → enter flag appends keypress.
**Invariant:** (1) The modifier for paste/select-all is PLATFORM-dependent at generation time (`command` vs `ctrl`) — hardcoding ctrl breaks macOS. (2) The dependency bootstrap lives inside the EMITTED code, so it heals on the TARGET machine during execution, not on the agent host. (3) repr()-quoting of all interpolated strings keeps arbitrary text injection-safe within Python string semantics. (4) write() cannot produce non-ASCII (layout-dependent) — that limitation, not speed, drives the split.
**Probe:** `grep -n 'ord(char) > 127' gui_agents/s3/agents/grounding.py` → :451.
**Probe:** `grep -n "command' if self.platform == 'darwin'" gui_agents/s3/agents/grounding.py` → :446 and :456.
**Probe:** `grep -n 'pip., .install., .pyperclip' gui_agents/s3/agents/grounding.py` → :435.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "type unicode pyperclipboard overwrite", limit: 5 });
```

## Verdict
Adopt content-aware typing with clipboard fallback and target-side dependency healing; adapt the installer commands to your distro; omit the embedded sudo password literal.
