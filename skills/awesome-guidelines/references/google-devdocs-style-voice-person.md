<!-- capsule-v2 -->
# Voice and person — is prose conversational, you-focused, and actively voiced?

**Source:** Google developer documentation style guide §Voice and tone, §Second person, §Active voice. **Question:** Does the doc address the reader as you with active imperative steps and without please/buzzword filler?

## Voice seam
**Path/Symbol:** developer guides, API intros, procedural pages.
**Signature:** conversational friendly tone; you/your; active voice; imperative steps.
**Data Shape:** identify audience near start; we/our only for org as author.

### Decisive pattern
```
In the Google Cloud console, go to the Monitoring page.
Click **Create instance**.
The server sends an acknowledgment.
```

**Flow:** write conversationally and respectfully — knowledgeable friend, not pedantic or frivolous → address reader as **you/your** for tasks; use **imperative** for instructions (Click Submit) — not please → use active voice so doer is clear; passive only when emphasizing object, de-emphasizing actor, or actor irrelevant → use third person for what software/end users do when documenting APIs → identify audience (developer, admin) early and stay consistent → we/our OK only when organization is explicit antecedent → avoid buzzwords, simply/easy/quickly, let's, please note/at this time, exclamation marks, pop-culture refs, ableist figurative language, denigrating phrasing → prefer short clear sentences for global readers.
**Invariant:** please in steps, default passive, or unexplained we when you is meant fails Google devdoc voice review.
**Probe:** grep `\bplease\b` in procedures; passive by/z scan; second-person consistency check.

## Exceptions seam
**Flow:** passive OK for "The file is saved" or emphasizing results without blaming reader → formal API facts may use third person for elements while keeping you for tasks.
**Invariant:** passive that hides who must act when reader must act fails clarity rule.
**Probe:** reader responsibility trace on critical steps.

## Verdict
You/imperative/active default, friendly not frivolous, no please in steps. Learning note: `google-devdocs-style-learning-note.md`.
