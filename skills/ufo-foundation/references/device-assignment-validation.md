<!-- capsule-v2 -->
# Device-assignment validation and strategy dispatch — When should a constellation be rejected before execution for missing device targets?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How does the orchestrator guarantee every task has a real device target before running, and how are automatic assignments chosen?

## Fail-fast validation + named-strategy assignment
**Path/Symbol:** `galaxy/constellation/orchestrator/orchestrator.py:TaskConstellationOrchestrator._validate_existing_device_assignments` (:298-355); `galaxy/constellation/orchestrator/constellation_manager.py:ConstellationManager.assign_devices_automatically` (:132-185); thin orchestrator delegate `TaskConstellationOrchestrator.assign_devices_automatically` (:747-763).
**Signature:** `def _validate_existing_device_assignments(self, constellation: TaskConstellation) -> None` (raises); `async def assign_devices_automatically(self, constellation: TaskConstellation, strategy: str = "round_robin", device_preferences: Optional[Dict[str, str]] = None) -> Dict[str, str]`.
**Data Shape:** Each TaskStar carries `target_device_id`; validation compares that set against `device_manager.get_all_devices()` keys; assignment returns `{task_id → device_id}` and also writes it onto each task.

### Decisive source
```python
# validation — collect ALL problems into ONE error
for task_id, task in constellation.tasks.items():
    if not task.target_device_id:
        tasks_without_device.append(task_id)
    elif task.target_device_id not in valid_device_ids:
        tasks_with_invalid_device.append(f"{task_id} (assigned to unknown device: ...)")
if error_parts:
    raise ValueError(error_msg)   # lists gaps, invalid ids, AND available devices

# strategy dispatch
if strategy == "round_robin": ...
elif strategy == "capability_match": ...
elif strategy == "load_balance": ...
else:
    raise ValueError(f"Unknown assignment strategy: {strategy}")
for task_id, device_id in assignments.items():
    if task := constellation.get_task(task_id):
        task.target_device_id = device_id
```

**Flow:** orchestrator startup (or loop re-validation after merges) checks every task has a registered device; when assignments are absent, callers invoke assign_devices_automatically which picks a strategy, computes {task→device}, writes `target_device_id`, and returns the map. Missing manager, zero available devices, or unknown strategy all raise ValueError before any task executes.
**Invariant:** no task may start executing with an empty or unregistered `target_device_id`; validation errors must enumerate every offending task plus the available-device set in one message (fix-everything-at-once diagnostics), not fail on the first gap.
**Probe:** `tests/test_orchestrator_refactored.py:335-350` (`test_assign_devices_automatically`) pins round_robin assigning every added task exactly one entry. Direct source reads confirmed both ranges against graph snippets.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", name_pattern: ".*(assign_devices_automatically|_validate_existing_device_assignments).*", limit: 10 });
```

## Verdict
Adopt the contract: pre-flight whole-graph resource binding with aggregate error reporting, plus pluggable named strategies that write their decision back onto the work item. Adapt strategy set to your resources (UFO's round_robin/capability_match/load_balance assume heterogeneous remote devices). Omit the preferences dict unless planners need per-task affinity hints.
