<!-- capsule-v2 -->
|# Self-learning QA memory — how does an Easy Apply bot answer unseen screening questions and get smarter every run?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58` (2025-11-28); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** how do you combine static phrase-routed answers with a persistent Q&A ledger so one-time manual answers are replayed forever, without ever asking the same question twice?

## ans_question ladder + qa.csv append-only memory
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.ans_question` (:601–653), qa.csv bootstrap (:144–155), error-loop caller `send_resume` (:504–521); `qa.csv` (repo-root artifact).
**Signature:** `ans_question(question_lowered: str) -> str`; side effect: appends `(question, answer)` to `qa.csv` via pandas when the question is new; `self.answers: dict[str,str]` hydrated at construction from `pd.read_csv('qa.csv')` rows.
**Data Shape:** two-column CSV `Question,Answer`, append mode (`mode='a', header=False`) — never rewritten; the dict is the read cache, the CSV is durable state. Ladder answers are plain strings: `"1"`, `"Yes"`, `"No"`, `"Male"`, `"Wish not to answer"`, config values (`self.salary`).

### Decisive source
```python
# STATIC LADDER — first substring match wins; order IS the policy
if "how many" in question:      answer = "1"
elif "experience" in question:  answer = "1"
elif "sponsor" in question:     answer = "No"
elif "salary" in question:      answer = self.salary        # config-injected
elif "gender" in question:      answer = "Male"
elif "race" in question:        answer = "Wish not to answer"
...
else:
    answer = "user provided"    # sentinel for unanswerable — human takes over
    time.sleep(15)              # pause the modal loop so a human can type

# PERSISTENT MEMORY — only NEW questions hit disk (dedupe by exact string)
if question not in self.answers:
    self.answers[question] = answer
    pd.DataFrame({"Question": [question], "Answer": [answer]}).to_csv(
        self.qa_file, mode='a', header=False, index=False)
```
The error-loop integration is what makes it self-healing: inside `send_resume`, while validation errors exist → sleep 5 s → re-collect fields → `process_questions()` re-answers EVERY visible field via the ladder+memory → retry until `"application was sent"` appears in page source or the easy-apply button resurfaces (modal lost ⇒ abandon).
**Flow:** field text → answers-dict hit? use it : run ladder → unanswerable? sentinel + 15 s human window → record new pairs to CSV → error loop re-invokes until submit succeeds.
**Invariant:** the dict is populated BEFORE any answering (constructor), so previously-seen questions NEVER take the ladder path again — memory overrides heuristics; the CSV is append-only with no header on appends so the constructor's `pd.read_csv` round-trip stays stable; unanswered questions surface as the literal sentinel `"user provided"` rather than silence.
**Probe:** repo has no automated tests — coverage caveat. Deterministic probe: `awk 'NR>=603 && NR<=634 && /elif/' easyapplybot.py | wc -l` ⇒ 15 (`elif`s) plus the leading `if` at :603 ⇒ 16 ladder branches; `head -2 qa.csv` shows the two-column schema; graph anchor `EasyApplyBot.ans_question` resolves uniquely in project `LinkedIn-Easy-Apply-Bot`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "ans_question process_questions qa answers", limit: 5 });`

## Verdict
Adopt the three-layer answer stack: (1) persistent Q&A memory consulted FIRST, (2) keyword-ladder fallback with config-injected values, (3) loud sentinel + timed human-takeover window for the unknown — plus append-only persistence keyed by exact question text so the bot converges to fully-automatic over runs. Adapt the ladder's ethically fraught defaults (auto-"Male"/auto-"Yes" on "do you" questions) into explicit per-user config; harden the exact-string dict key with normalization (casefold + whitespace collapse). Omit the buggy dead branch (`if "Yes" or "No" in answer` — always true; and `form.find_element` called on a LIST crashes before it could matter): porting that verbatim would import broken code. Contrast: form-question-answering (Auto_job_applier) routes by WIDGET TYPE with audit tuples but has NO cross-run memory; this pattern adds the missing time dimension — widget dispatch decides HOW to answer, QA memory decides WHAT to answer.
