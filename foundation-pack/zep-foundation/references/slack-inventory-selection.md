<!-- capsule-v2 -->
# Slack export inventory & selection — how are four conversation indexes, wrapper folders, and path traversal handled?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does the loader enumerate conversations across channels/groups/dms/mpims and never drop or mislabel data silently?

## Inventory / select / readers
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/slack.py:39` (`CONVERSATION_FILES`), `:52` (`EXPORT_MARKER_FILES`), `:64` (`DEFAULT_SKIP_SUBTYPES`), `:129-231` (`_DirReader`/`_ZipReader` incl. `_unwrap`, `_resolve_export_path`, `day_files`), `:435` (`_inventory`), `:470` (`_folder_inventory`), `:515` (`_select`), `:536` (`_warn_skipped_types`).
**Signature:** `_select(inventory)` raises ConfigurationError for requested channels that are missing OR excluded by conversation_types (two distinct messages). Default conversation_types = public_channel ONLY.
**Data Shape:** `_Conversation(folder, label, kind, member_ids)`; DM/group-DM labels = member display names joined (folders are opaque D01ABC234 / mpdm-* slugs).

### Decisive source
```python
# _unwrap — an export stays an export once extracted; without re-rooting,
# the wrapper reads as one conversation whose only files are index files
# and a valid export ingests NOTHING.
if any((root / marker).is_file() for marker in EXPORT_MARKER_FILES):
    return root
children = [child for child in root.iterdir() if child.is_dir()]
...
# _DirReader._resolve_export_path — reject traversal/symlinks outside root:
candidate.relative_to(self.path)  # ValueError ⇒ ConfigurationError

# day_files: only .json DIRECTLY inside the folder — deeper files belong to
# another conversation or attachments; reading them would file one
# conversation's messages under another's name and type.
```

**Flow:** pick reader by is_file() → unwrap single wrapping folder (zip: shared prefix via marker files; dir: sole child dir carrying markers; symlink-out rejected) → read all four indexes → dedupe folders → label DMs by members → fall back to folder-name typing only when NO indexes exist (with "could not be determined" warning — private vs public folder indistinguishable) → filter types then channels → warn_skipped_types enumerates what was found but not selected ("never dropped in silence") with the exact conversation_types= to pass.
**Invariant:** Selection errors name remedies (available conversations, missing types); unselected-but-present conversations produce a warning with counts, never silence. Path validation runs on EVERY folder/index entry (`_validated_folder` rejects `.`, `..`, `/`, `\`) because export content is attacker-shaped data.
**Probe:** `grep -c 'def test' ingestion/tests/test_slack_loader.py` → 82 incl. wrapper/traversal/skip-warning fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "SlackExportLoader inventory select conversation_types unwrap zip", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt marker-based export-root unwrapping + dual-reader interface + loud skip accounting + traversal rejection; adapt index filenames to your export format; omit Slack markup regexes.
