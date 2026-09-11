<!-- capsule-v2 -->
# Ticket-progress persistence plane — how do you persist long-running job progress for a polling UI without write amplification?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What makes a per-job progress document cheap to save from a hot loop, and what does the read side assume?

## TicketProgress._save: delta-gated $set upsert with enum round-trip; async saves share the global thread registry
**Path/Symbol:** `sweepai/utils/progress.py:TicketProgress.load` (:179–185), `_save` (:193–214), `save` (:216–223), `refresh` (:187–191), `wait` (:224–263), `create_index` (:265–269); read route `sweepai/api.py:progress` (:247–250).
**Signature:** `load(cls, tracking_id: str) -> TicketProgress` (classmethod); `_save(self)`; `save(self, do_async: bool = True)`; route `GET /ticket_progress/{tracking_id}` returns `ticket_progress.dict()`.
**Data Shape:** One Mongo doc per `tracking_id` in db `progress`, collection `ticket_progress`, UNIQUE index on `tracking_id`. Doc = full `model_dump()` of the pydantic tree (context/search/planning/coding progress, status, user_state) minus the `prev_dict` field.

### Decisive source
```python
def _save(self):
    # Can optimize by only saving the deltas
    try:
        if MONGODB_URI is None:
            return None
        # cannot encode enum object
        if isinstance(self.status, Enum):
            self.status = self.status.value  # Convert enum member to its value
        if self.model_dump() == self.prev_dict:
            return
        current_dict = self.model_dump()
        del current_dict["prev_dict"]
        self.prev_dict = current_dict
        collection.update_one(
            {"tracking_id": self.tracking_id}, {"$set": current_dict}, upsert=True
        )
        self.status = TicketProgressStatus(self.status)   # restore enum after dump
    except Exception as e:
        logger.error(str(e) + "\n\n" + str(self.tracking_id))

def save(self, do_async: bool = True):
    if do_async:
        thread = Thread(target=self._save)
        thread.start()
        global_threads.append(thread)      # SAME registry as ChatLogger writes + latest-wins teardown
    else:
        self._save()
```

**Flow:** hot loop mutates the in-memory TicketProgress and calls `save()` → a throwaway thread re-dumps the model and compares against `prev_dict` (the last PERSISTED snapshot) → identical ⇒ return without touching Mongo (the delta gate kills no-op write amplification) → different ⇒ strip `prev_dict`, store it as the new baseline, `$set`-upsert the whole doc, restore the enum. `load` is the inverse (`cls(**doc)`); `refresh()` reloads and does an in-place `__dict__.update` so other references see fresh state; the UI polls `GET /ticket_progress/{tracking_id}`.
**Invariant:** The delta gate compares against the last SAVED state, not the last mutated one — two rapid saves of the same value produce exactly one write. The enum→value→enum round-trip mutates `self.status` in place around the dump; a port using a serializer that handles enums can drop it. Everything is fail-soft: Mongo unset ⇒ silent no-op, any exception ⇒ logged with the tracking_id, never raised into the job. `load` has NO missing-doc guard (`find_one` → None ⇒ `cls(**None)` raises TypeError), and the route has no None-guard either — the read side assumes Mongo is configured and the id exists. `wait(wait_time=20)` stamps `user_state` WAITING + deadline but its polling loop is entirely commented out — the user-breakpoint feature is DEAD at pin; do not port it as working.
**Probe:** No offline unit test exists (MongoDB-dependent — coverage caveat). Deterministic probes at pin: `grep -c 'global_threads.append' sweepai/utils/progress.py` → 1; `grep -n 'prev_dict' sweepai/utils/progress.py | wc -l` → 4; the dead wait-loop is commented code visible at :235–255.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "TicketProgress save load tracking_id ticket progress", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source read of
// progress.py whole + api.py:247-250 at pin substituted — see verification.md pass 3.
```

## Verdict
Adopt the delta-gated whole-doc `$set` upsert keyed on a unique job id, async saves parked in the process-wide thread registry (so shutdown/teardown sees them), and fail-soft persistence that never raises into the job. Add the missing-doc guard on the read path if your UI polls unknown ids. Omit the commented-out breakpoint wait loop and the legacy AssistantConversation models in the same file (superseded product surface).
