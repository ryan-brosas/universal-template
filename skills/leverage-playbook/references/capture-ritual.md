# Capture Ritual

Source: Tom, 7/26/26 (verbatim block in `~/.agents/essentials/discord-material/raw/block-003-8261d887b772.md`).

## The exact prompt

> Recall what we've done and capture everything that was done, all the small stuff and edge cases, into skills, in a separate folder. Do your due diligence to capture all the small stuff and edge cases we've covered across the session.

Executed honestly:
```text
Recall what we've done and capture everything into skills into a separate folder.
Do your due diligence to make sure we capture all of the small stuff and edge cases
we've covered across the session.
```

## When
After the session has compacted 3–4 times — long enough that the model has an intuition but needs recall to preserve the small stuff that compaction drops. Every session that produced something reusable earns this pass; the key is it is done *during* or *end of* the session, not prototyped away forever.

## Procedure
1. Start with a deliberate "impossible first" attempt so the missing tools/skills surface (browser use, computer use, API access...).
2. Let it do it once really well (~2h initial), then force 2–3 more runs to shake out edge cases (20m each).
3. Then bind the results into skills + `references/` capsules (+ markdown docs where required post-code) and keep the code around — code is an asset; "code from scratch is cheap, code you hold is valuable."

## Why
- Your biggest assets are skills + held code.
- A good output is enough — you don't have to prove the code "good": keep it, generalize via "This design we have looks really good. Help me improve and generalize the code for this, while keeping the design output we have today."
- Compounding: 2h → 20m → 30s per extension, because the model looks back at your old code and practices.
