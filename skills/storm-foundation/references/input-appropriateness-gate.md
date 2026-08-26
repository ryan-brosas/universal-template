<!-- capsule-v2 -->
# Input-appropriateness gate — how do you front a research pipeline with cheap deterministic checks plus one small-model verdict?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the ordered gate ladder (length → charset → LLM judgment) and its fail-closed semantics?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:user_input_appropriateness_check` (:714-766) + `purpose_appropriateness_check` (:769-793).
**Signature:** `user_input_appropriateness_check(user_input: str) -> str` returning `"Approved"` or a human-facing rejection string.
**Data Shape:** Verdict strings are user-displayed messages; reject reasons 1-4 (harm, non-English, personal experience, non-research intent) map to fixed apology texts that disclose GPT-4o-mini false-positive risk.

### Decisive source
```python
my_openai_model = LitellmModel(
    model="azure/gpt-4o-mini", max_tokens=10, temperature=0.0, top_p=0.9,
)
if len(user_input.split()) > 20:
    return "The input is too long. Please make your input topic more concise!"
if not re.match(r'^[a-zA-Z0-9\s\-\"\,\.\?\']*$', user_input):
    return "The input contains invalid characters. The input should only contain a-z, A-Z, 0-9, space, -/\"/,./?/'."
# LLM verdict contract: model must answer "Yes." or "No. The input violates reason [1/2/3/4]"
response = my_openai_model(prompt)[0].replace("[", "").replace("]", "")
if response.startswith("No"):
    match = regex.search(r"reason\s(\d+)", response)
    ...reject_reason_info lookup...
except Exception as e:
    return "Sorry, the input is inappropriate. Please try another topic!"   # FAIL-CLOSED
return "Approved"
```

**Flow:** Deterministic length cap (>20 words) → ASCII-charset allowlist regex → single `azure/gpt-4o-mini` call (`max_tokens=10`, temperature 0.0) judging against four enumerated inappropriateness classes → reason-number parsed out of the reply → unknown/missing reason degrades to the generic rejection → ANY exception in the LLM path rejects.
**Invariant:** (1) Fail-CLOSED on infrastructure errors: an API outage blocks topics rather than admitting everything — invert only with explicit product sign-off. (2) The purpose-check twin fails closed to "please provide a more detailed explanation". (3) Bracket-stripping before parsing exists because the model tends to wrap the reason number in `[n]` — the same bracket vocabulary as citations, deliberately neutralized here. (4) The checker instantiates its own LitellmModel; it does NOT reuse pipeline LM configs, so it stays cheap and isolated from stage accounting.
**Probe:** deterministic pin GREEN — utils.py:714-766 read whole this pass; graph resolves `user_input_appropriateness_check` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "user_input_appropriateness_check reject reason", limit: 10 });
```

## Verdict
Adopt the cheap-deterministic-first + fail-closed-small-model gate for any public research endpoint; adapt the class taxonomy and copy; omit the hardcoded azure/gpt-4o-mini by injecting your own guard model. Caveat: no upstream tests; source-pinned.
