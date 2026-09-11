<!-- capsule-v2 -->
# uno-set-cell-values-template — How are spreadsheet writes performed without GUI clicking?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How does the set_cell_values action template a UNO automation script, and what escaping discipline applies?

## UNO template seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:SET_CELL_VALUES_CMD` (:51-176) + `OSWorldACI.set_cell_values` (:527-540); skipped on non-linux (worker reset :64-67).
**Signature:** `set_cell_values(cell_values: Dict[str, Any], app_name: str, sheet_name: str) -> str` returning the formatted template.
**Data Shape:** Template = a COMPLETE python program: kill stale TCP TIME-WAIT on port 2002 (sudo) → start soffice UNO listener → resolve context/desktop → enumerate desktop Components → identify doc type via supportsService → match Calc by title → per-cell write with TYPE dispatch.

### Decisive source
```python
# double-brace escapes make the template str.format()-safe while keeping dict literals
new_cell_values_idx = {{}}
...
raise ValueError(f"Could not find sheet {{sheet_name}} in {{app_name}}.")
# single braces remain format holes:
set_cell_values(new_cell_values={cell_values}, app_name="{app_name}", sheet_name="{sheet_name}")

# value-type dispatch inside the template
if isinstance(value, (int, float)): cell.Value = value
elif isinstance(value, str):
    if value.startswith("="): cell.Formula = value   # formulas via leading '='
    else: cell.String = value
elif isinstance(value, bool): cell.Value = 1 if value else 0
elif value is None: cell.clearContents(0)
```

**Flow:** model calls the action → `.format(cell_values=…, app_name=…, sheet_name=…)` fills the three holes → returned string is exec'd by the harness INSIDE the OSWorld VM → UNO bridge writes cells directly.
**Invariant:** (1) The template mixes TWO escaping regimes — `{{...}}` for literal dicts/f-strings inside the template vs `{hole}` for format parameters; editing either class blindly breaks .format at emission time. (2) bool is checked AFTER int/float because bool IS an int subclass — reordering turns True into 1 silently. (3) Strings starting with '=' become formulas, not text. (4) The sudo password literal and port-2002 hygiene are OSWorld-VM specifics. (5) `_norm_name` handles unicode-escaped titles before matching (:67-81).
**Probe:** `grep -c 'cell_values={cell_values}' gui_agents/s3/agents/grounding.py` → 1 (:175).
**Probe:** `grep -n 'isinstance(value, bool)' gui_agents/s3/agents/grounding.py` → :165.
**Probe:** `grep -n 'supportsService("com.sun.star.sheet.SpreadsheetDocument")' gui_agents/s3/agents/grounding.py` → :56.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "set_cell_values UNO soffice", limit: 5 });
```

## Verdict
Adopt template-emitted native-API automation as an alternative to pixel-level GUI interaction when a scripting bridge exists; adapt the bridge (UNO→AppleScript/UIA/xdotool); omit the OSWorld socket/password plumbing. The brace-class discipline is mandatory when porting.
