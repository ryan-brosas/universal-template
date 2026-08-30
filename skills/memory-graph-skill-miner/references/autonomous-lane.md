# Autonomous lane task — model-driven, no scripts

Autonomous recurring lane for memory-graph-skill-miner on hosts with a
recurring-trigger surface (cron, systemd user timer, DSH Factory lane, pi
recurring task). There is **no scheduler script and no lane-dumping tool**: the
trigger only wakes the model, and the model does ALL steps itself — reads the
ledger, self-selects the next lane, mines the repo, writes the learning note,
produces capsules, syncs OpenViking, and updates the ledger.

## Trigger (wake the model, nothing else)

A recurring job runs this headless command (or the equivalent on the host):

    pi -H --no-approve --skill ~/.agents/skills/memory-graph-skill-miner \
       -p "Run one memory-graph-skill-miner autonomous lane. Load the task contract at ~/.agents/skills/memory-graph-skill-miner/references/autonomous-lane.md and follow it exactly."

Cron example (every 6 hours, one lane per fire; if a lane is still running the
driver-less model re-reads the ledger and skips rows whose lease is live):

    0 */6 * * * /home/utopia/.local/share/mise/installs/node/26.7.0/bin/pi -H -p "Run one memory-graph-skill-miner autonomous lane. Load the contract at ~/.agents/skills/memory-graph-skill-miner/references/autonomous-lane.md and follow it exactly."

systemd user timer: same command in a .service with .timer OnCalendar=*-*-* *:00:00.

DSH Factory: native `standard` Agent preset lane with the same prompt (never
`fabric`/`code` constructors — the batching shortcuts this lane forbids).

## Contract — the model is the scheduler AND the miner

1. **Self-select the lane** by reading the canonical ledger
   (/mnt/hdd/utopia/inspo/.skill-mining-work/llm-repo-learning.md) Status board.
   Pick the row whose status is `active` with the OLDEST `last-pass` date;
   pages `blocked` and `complete` are parked. Read the selected row and its
   work record ({state,research,verification}.md) before deciding. If no
   active row remains, return [DONE] and stop.
2. **Own the lane**: announce the chosen slug + leaf. Never touch another row,
   board line, leaf, or repository for the rest of the run.
3. **Learning note FIRST**: write
   .skill-mining-work/<slug>/research.md (mental model, covered/partial/uncited
   seams, porter questions) before any production edit. This order is
   mandatory and is the proof the model learned before producing.
4. **Seven-gate procedure, executed by the model with native MCP calls**
   (get_architecture, search_graph, trace_path, get_code_snippet,
   check_index_coverage) + exact source/test reads — never scripts, never
   generated bundles of calls. Source and direct tests are the authority.
5. **Author 5-8 capsule-v2 outcomes** (target 6) in the target leaf refs, each
   with Source/Path.Symbol/Signature/Data Shape/decisive source excerpt/Flow/
   Invariant/Probe/Retrieve/Verdict — or record an evidenced closure/blocker.
6. **Manual-learning enforcement**: enumerate each seam's explicit graph search,
   trace, snippet, coverage check, decisive source read, direct test read, and
   manually-authored file. NO INSTALLATION, NO SCRIPT MAKING: never install a
   package/tool (pip/npm/cargo/etc.), never write or generate a helper script,
   one-liner, shell loop, heredoc, xargs/find pipeline, awk/sed/jq transform,
   or any other automation to do the work; never create a cron/systemd unit or
   modify host config. Only the host's existing native tools (the CLI's own
   file/MCP surfaces, the installed `ov` CLI for OpenViking) may be used, and
   only for the step they are documented for. Certify no run_code, no generated
   scripts, no delegation to subagents, no awk/sed/jq/pipeline transforms for
   discovery or parity. A shortcut-tainted artifact does not count; redo
   manually or report partial/blocked.
7. **OpenViking sync**: push the note + new capsule files into
   viking://resources/llm-repo-learning-passN-<slug>/ (memadd/ov); verify a
   newly cited symbol is findable; record the probe. Unavailable daemon =
   record degraded path and continue; never block the pass on OpenViking.
8. **Update the ledger** row AND its Status board line in the same write:
   fresh re-read immediately before, exact own-row edit, post-write read-back.
   Update inspection/source-name of parity (loader==map==disk), PASS/result
   counts, blockers, and concrete NEXT-PASS TARGETS.
9. **Return** PASS with paths+counts+evidence, partial/blocked with reasons, or
   [SILENT] only when the repo is fully covered and the records prove no
   uncited or refactorable seam remains.

## Boundaries
- **No installation, no script making.** The lane never installs anything
  (no pip/npm/cargo/apt installs), never writes or generates helper scripts
  (no .py/.sh/.js/.mjs/.ts helpers, one-liners, loops, heredocs, xargs/find
  pipelines, awk/sed/jq transforms, temporary automation, cron/systemd units,
  or any other tool), and never modifies host config. Only the native tools
  that already exist on the host are used — each only for its documented
  purpose. If the work needs a capability the host doesn't already have (a
  test runner, a graph server, a sync CLI), record it as a blocker in the
  work record; never build it.
- The lane may write only its own paths and owned files: the leaf
  dir, .skill-mining-work/<slug>/{state,research,verification}.md, and
  llm-repo-learning.md (own row + own Status line only).
- Never edit the source checkout, questions/keys, another leaf or lane's rows.
- Working locks: the model holds the lease by claiming at run start; release
  (mark released with outcome) on any terminal result; a stale lease older
  than the lease TTL is reclaimable by the next run (crash-safe retry).
- No parallel lanes on the same row; if the host has no ship/lease surface,
  serialize lanes by reading the ledger first and skipping rows with a live
  lease marker.

## Why not a scheduler script

A script can read ledger metadata but cannot read the source, judge decisive
excerpts, execute RED/GREEN gates, or produce audio capsule evidence. The model
IS the loop: it chooses, learns, and delivers; the trigger only wakes it.
