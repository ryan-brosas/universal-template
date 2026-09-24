# Recover missing task artifacts

Use when a needed reference, generated image or build source has disappeared from
its working path. This is bounded task recovery, not filesystem forensics or
permission to inspect unrelated histories. Do not restore an intentionally
withdrawn input without permission.

## Distinguish a missing path from missing data

Check surviving project masters and the authorized destination first. Locate the
exact session and relevant entry IDs through available history tools; repository
name or recency alone does not identify the right session. Ask the user to resend
only what cannot be recovered through an authorized route, with the concrete
limitation stated.

A normalized text result may retain only an image marker, while the original
attachment still exists. Missing bytes in that projection do not prove absence
from the host's retained entries. Conversely, a marker does not prove that the
bytes were retained. Discover an attachment/export capability or the installed
host's supported SDK before concluding either way. Do not bypass a capability or
access restriction by opening a different surface.

## Recover the smallest useful payload

- Prefer a supported export or public SDK entry reader. Installed documentation
  and current source own the API; do not manually parse session JSONL or promote
  a private testing export into a stable dependency.
- Check read-side effects. A loader can repair a missing trailing newline or migrate
  a file even when called only to read it. If needed, read a private snapshot rather
  than the live session. Keep the snapshot access-restricted and outside deliverable
  or shared folders, and remove only that owned snapshot after recovery.
- Select known task entries and image blocks or explicitly identified source
  payloads, not a whole-history export. Preserve the original bytes and MIME type.
  Save recovered files into persistent task storage without overwriting user edits.
  A retained image may be resized or recompressed, so do not assume it is an
  editable master or byte-identical to the original file.
- Inspect recovered source before executing it as a rebuild step. Recovery of a
  tool-call payload does not authorize blindly replaying its commands, uploads or
  other side effects. Recover files, not an automatic replay of the session.
- Capture repository-held artifacts without competing for that repository's
  mutable state. Read files and objects through a private index or a copy, and
  leave locks, staging and HEAD as they were; never clear another process's lock,
  stage, unstage or reset merely to rescue output.
- Carry the source record's own identity through derived projections. A normalized
  field, summary or re-export can drop the model, author or revision the original
  record carried; read identity from that record instead of inferring it from the
  current model, a nearby change event or traversal position, and report it absent
  when it is genuinely unavailable.

## Verify before continuing

Decode and inspect images; check dimensions, expected content, and hashes when a
known original is available. If source can be rebuilt, compare a fresh render
against the recovered preview and verify any approved geometry remains unchanged.
Keep exact byte recovery, visual equivalence and editability as separate claims.

The recovery can succeed without identifying why the working file disappeared.
Do not attribute the loss to a cleaner, harness or user without evidence, or change
machine-wide cleanup settings to suppress an unexplained event. If retention or
authorized access is unavailable, preserve what survives and ask only for the
missing input. For visual delivery, resume the existing
[asset checkpoint workflow](../../visual-asset-iteration/README.md); host recovery
alone does not prove that a canvas was updated.
