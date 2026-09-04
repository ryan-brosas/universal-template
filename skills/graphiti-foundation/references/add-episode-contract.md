<!-- capsule-v2 -->
# add_episode — the full ingestion contract (types, exclusions, sagas, custom instructions)

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** what does a full episode-ingestion API expose so callers can steer extraction without touching internals?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/graphiti.py`: `add_episode` (:980-1063+), `AddEpisodeResults` (:114), `add_triplet` (via `AddTripletResults` :132), `retrieve_episodes` (:927).
**Signature:**
```ts
add_episode(
  name, episode_body, source_description, reference_time,
  source = EpisodeType.message,
  group_id?, uuid?,
  update_communities = False,
  entity_types?: dict[str, type[BaseModel]],       # typed entity schemas
  excluded_entity_types?: list[str],               # e.g. ['Entity'] to drop default
  previous_episode_uuids?: list[str],              # else most-recent by created_at
  edge_types?: dict[str, type[BaseModel]],
  edge_type_map?: dict[tuple[str,str], list[str]], # (source_type, target_type) -> edge types
  custom_extraction_instructions?: str,            # injected into extract prompts
  saga?: str | SagaNode, saga_previous_episode_uuid?,
) -> AddEpisodeResults
```
**Data Shape:** episodes link into sagas via `HAS_EPISODE` edges; consecutive saga episodes chain via `NEXT_EPISODE`; `saga_previous_episode_uuid` skips the newest-episode query when adding in sequence.

### Decisive source
```ts
entity_types : dict[str, BaseModel] | None   # typed entity models for extraction
excluded_entity_types : list[str] | None     # entities classified into these are NOT added
edge_type_map : dict[(src,tgt), list[str]]   # constrain which edge types may connect type pairs
custom_extraction_instructions : str | None  # extra steering text inside extract prompts
# Sagas: HAS_EPISODE connects saga->episode; NEXT_EPISODE chains consecutive episodes.
```

**Flow:** validate + resolve group → get/create saga (`_get_or_create_saga`) → chunk if dense (`should_chunk`) → extract nodes+edges (typed schemas + exclusions + custom instructions) → dedup/resolve against `get_relevant_nodes/edges` + invalidation candidates → persist via driver ops → optionally update communities.
**Invariant:** extraction is steerable per call (types/exclusions/instructions) without forking the pipeline; saga chaining is O(1) when the caller passes `saga_previous_episode_uuid`; community updates are opt-in.
**Probe:** `tests/` graphiti tests (typed entity extraction; excluded types absent from graph; custom instructions reach prompts; NEXT_EPISODE chaining with explicit prev uuid).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "add_episode entity_types excluded_entity_types edge_type_map custom_extraction_instructions saga", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the steerable ingestion signature (typed entity/edge schemas, exclusions, edge_type_map, custom instructions, saga chaining); adapt defaults to host.
