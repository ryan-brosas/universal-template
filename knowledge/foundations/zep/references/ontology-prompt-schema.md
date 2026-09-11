<!-- capsule-v2 -->
# Ontology prompt-as-schema — how do Pydantic classes steer extraction classification?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** What does the default ontology teach about writing entity/edge types an LLM will apply correctly?

## default_ontology.py
**Path/Symbol:** `ontology/default_ontology.py:1-139` (`User`, `Assistant`, `Preference`, `Location`, `Event`, `Object`, `Topic`, `Organization`, `Document`; edges `LOCATED_AT`, `OCCURRED_AT`); maps `ZEP_NODE_ONTOLOGY`/`ZEP_EDGE_ONTOLOGY`/`ZEP_EDGE_TYPE_MAP`.
**Signature:** Each type = a Pydantic BaseModel whose docstring and Field descriptions ARE the extractor's instructions.
**Data Shape:** Singleton types (User, Assistant) say so in-docstring; fallback types (Object, Topic) carry explicit "ONLY as a last resort" checklists naming the types to try first.

### Decisive source
```python
class Preference(BaseModel):
    """
    IMPORTANT: Prioritize this classification over ALL other classifications
    except User and Assistant.

    Represents entities mentioned in contexts expressing user preferences,
    choices, opinions, or selections. Use LOW THRESHOLD for sensitivity.

    Trigger patterns: "I want/like/prefer/choose X", "I don't want/dislike/
    avoid/reject Y", "X is better/worse", ... Here, X or Y should be
    classified as Preference.
    """

ZEP_EDGE_TYPE_MAP = {
    ("Event", "Entity"): ["OCCURRED_AT"],
    ("Entity", "Location"): ["LOCATED_AT"],
}
```

**Flow:** ontology registered per existing graph via client.graph.set_ontology(entities=..., edges=..., graph_ids=[...]) BEFORE ingestion — zep-ingest writes only into graphs that already exist and already carry their ontology ("it is not retroactive").
**Invariant:** Classification guidance is priority-ordered prose INSIDE the schema: precedence rules ("Prioritize this classification over ALL other…"), trigger phrases, low/high sensitivity directives, and last-resort checklists. A porter who writes bare class names with no docstring guidance gets whatever the extractor's defaults decide. Edge map constrains (source-type, target-type) → allowed edge types.
**Probe:** `grep -c 'IMPORTANT' ontology/default_ontology.py` → 4 (Preference, Location, Object, Topic priority directives); direct test `ingestion/tests/test_example_ontology.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "ontology entity edge type preference classification", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt docstring-as-instruction schema authoring + priority ordering + trigger patterns; adapt types to your domain; omit Zep's set_ontology call shape.
