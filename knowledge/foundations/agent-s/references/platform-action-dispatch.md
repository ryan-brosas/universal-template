<!-- capsule-v2 -->
# platform-action-dispatch — How do open/switch actions emit per-OS launcher strings?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How do the platform-generic actions differ per OS, and why does linux switch use a script template instead of a hotkey?

## Platform dispatch seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:OSWorldACI.switch_applications` (:374-389) + `open` (:391-411) + module-level `UBUNTU_APP_SETUP` template (:30-48).
**Signature:** both are @agent_action methods returning executable strings; dispatch on `self.platform` ∈ {darwin, linux, windows}, else assert False.
**Data Shape:** darwin = Spotlight (`command+space`, typewrite, enter); windows = Win menu (hotkey('win'), write, enter); linux switch = wmctrl fuzzy-match+activate+maximize script; linux open = 'win' key + write + enter.

### Decisive source
```python
UBUNTU_APP_SETUP = f"""import subprocess;
import difflib; import pyautogui; import time;
pyautogui.press('escape'); time.sleep(0.5);
output = subprocess.check_output(['wmctrl', '-lx']); ...
window_titles = [line.split(None, 4)[2] for line in output];
closest_matches = difflib.get_close_matches('APP_NAME', window_titles, n=1, cutoff=0.1);
if closest_matches:
    ...
    window_id = line.split()[0]
subprocess.run(['wmctrl', '-ia', window_id])
subprocess.run(['wmctrl', '-ir', window_id, '-b', 'add,maximized_vert,maximized_horz'])"""
# switch_applications: UBUNTU_APP_SETUP.replace("APP_NAME", app_code)
```

**Flow:** action call → platform branch → emit string → harness exec()s it in the GUI session. Linux switch first presses Escape (dismiss menus), lists windows via wmctrl, fuzzy-matches titles (cutoff 0.1 = lenient), activates by window id, then maximizes.
**Invariant:** (1) The APP_NAME token is replaced with plain str.replace — an app_code containing the token or quotes breaks emission; values come from a model-chosen list so this is accepted risk. (2) Unsupported platforms ASSERT rather than fall back — silent wrong-OS behavior is treated as worse than crashing the turn. (3) Maximization is bundled into switch on linux only; darwin/windows never resize. (4) All emitted strings are self-contained single imports — they must run in a fresh exec namespace.
**Probe:** `grep -n "difflib.get_close_matches" gui_agents/s3/agents/grounding.py` → :39.
**Probe:** `grep -c 'Unsupported platform' gui_agents/s3/agents/grounding.py` → 2 (switch :389 + open :411).
**Probe:** `grep -n 'maximized_vert,maximized_horz' gui_agents/s3/agents/grounding.py` → :47.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "switch_applications open platform darwin linux windows", limit: 5 });
```

## Verdict
Adopt per-platform string emitters with assert-on-unknown; adapt launcher mechanics to your window manager; omit nothing — the lenient fuzzy match cutoff is what makes model-supplied app names work at all.
