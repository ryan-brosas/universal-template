<!-- capsule-v2 -->
# Faster-model tier gate — where does quota enforcement actually refuse a run, and what does each failure posture mean?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do you enforce per-user ticket quotas — when exactly do you refuse a run, and when (if ever) do you degrade it to a cheap model?

## use_faster_model tier ladder + determine_model_from_chat_logger raise
**Path/Symbol:** `sweepai/utils/chat_logger.py:use_faster_model` (:172–186); `sweepai/core/chat.py:determine_model_from_chat_logger` (:126–155) invoked inside `ChatGPT.call_openai` (:261); construction/consumption at `sweepai/handlers/on_ticket.py:135–158`.
**Signature:** `use_faster_model(self) -> bool`; `determine_model_from_chat_logger(chat_logger: ChatLogger | None, model: str) -> str`.
**Data Shape:** Reads per-user counters (`get_ticket_count()` monthly, `use_date=True` daily, `purchased=True` wallet) and boolean fields via `_get_user_field`; `active` is a constructor flag defaulting False (True only when a user intentionally opened the ticket).

### Decisive source
```python
def use_faster_model(self):
    if IS_SELF_HOSTED: return False
    if self.ticket_collection is None:
        logger.error("Ticket Collection Does Not Exist")
        return True                       # Mongo down ⇒ fail-closed to REFUSAL (handlers raise)
    ...
    return (
        (self.get_ticket_count() >= 5 or self.get_ticket_count(use_date=True) > 3)
        and purchased_tickets == 0
    ) or not self.active                  # auto-created ⇒ always degraded

# chat.py:126-155 (called from call_openai BEFORE every LLM call)
tickets_allocated = inf if chat_logger.is_paying_user() else 5
if tickets_count < tickets_allocated: return model
elif purchased_tickets > 0:            return model
else: raise ValueError("You have no more tickets!")
```

**Flow:** on_ticket builds ChatLogger(active=True) ONLY when MONGODB_URI exists (:135–139), computes `use_faster_model` once up front (:144), and a quota-driven True is a HARD REFUSAL — `raise Exception(FASTER_MODEL_MESSAGE)` ("You ran out of the free tier GPT-4 tickets!...") at on_ticket :150 and identically in on_comment :143; the GHA-autofix path reuses the same predicate as "Disabled for free users" (api.py:453). The ONLY cheap-model path is explicit `fast_mode` (user title tag), which sets `use_faster_model=True` AFTER the gate (:152–153) and then selects the cheaper model downstream (metadata `"gpt-3.5"` at on_ticket :173; claude-3-sonnet vs opus at sweep_bot.py:1463). The ledger increment fires off-thread only for fresh issues (:156–157, `gpt3=use_faster_model` so fast-mode tickets count in the gpt3 bucket) — and EVERY subsequent `call_openai` re-checks allocation through determine_model_from_chat_logger (:261), so a run that exhausts its allowance mid-flight fails at the next LLM call.
**Invariant:** Three distinct postures must not be conflated: (1) quota-driven `use_faster_model()==True` is a REFUSAL signal that both handlers convert into an immediate raise — NOT a silent degrade; (2) Mongo-unreachable makes `use_faster_model` return True, i.e. billing-store failure fails CLOSED to refusal, not to a slow tier; (3) `determine_model_from_chat_logger` raising ValueError is the MID-RUN refusal (allocation exhausted with purchased==0, or inactive non-payer non-consumer). Explicit fast_mode is the only path that actually degrades to a cheap model, and it is user-initiated. Self-hosted bypasses all of it (`IS_SELF_HOSTED` short-circuits every predicate). Payers get `inf` allocation so they are never refused by count alone — only consumers/trials hit the raise path with purchased==0.
**Probe:** No offline unit test exists for either function (MongoDB/env-dependent — coverage caveat). Deterministic probes at pin: `grep -c 'IS_SELF_HOSTED' sweepai/utils/chat_logger.py` → 4; `grep -n 'You have no more tickets' sweepai/core/chat.py` → line 134 and 153 (two distinct refusal messages); `grep -rn 'raise Exception(FASTER_MODEL_MESSAGE)' sweepai/handlers/` → on_ticket.py:150 + on_comment.py:143.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "use_faster_model determine model chat logger tickets allocated", limit: 10 });
// executed at pin: #1 ChatLogger.use_faster_model chat_logger.py 172-186;
// determine_model_from_chat_logger chat.py 126-155 rank-resolved exactly
```

## Verdict
Adopt the split between a cheap degrading predicate evaluated once per request and a hard allocation gate evaluated before every LLM call, plus fail-closed degradation when the billing store is unreachable. Adapt thresholds (500/20/5-monthly/>3-daily) to your plans; replace `inf-for-payers` with your real ceiling. Omit the `not active` blanket-degrade unless your product distinguishes user-initiated from auto-created runs.
