<!-- capsule-v2 -->
# Groups forest — how do you represent item grouping so root lookup, reparenting, and leaf enumeration are all safe?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter needs a grouping structure where every clip/composition/subtitle can participate in arbitrary nested groups (AV splits, selections), supports root queries during moves, and can never hide a corrupted cycle.

## Two mirrored maps: upLink + downLink over ALL ids
**Path/Symbol:** `src/timeline2/model/groupsmodel.cpp:GroupsModel` (whole model 19–481 core) — `getRootId` (193–208), `setGroup` (297–325), `groupItems`/`groupItems_lambda` (53–102), `createGroupItem`/`destructGroupItem_lambda` (116–154), `getLeaves` (265–282); fields `m_upLink`/`m_downLink`/`m_groupIds` (groupsmodel.hpp:224–228).
**Signature:** `int getRootId(int id) const` · `void setGroup(int id, int groupId, bool changeState)` · `int groupItems(const std::unordered_set<int> &ids, Fun &undo, Fun &redo, GroupType type, bool force = false)` · `std::unordered_set<int> getLeaves(int id) const`.
**Data Shape:** `m_upLink: id → parentId (-1 = root)` and `m_downLink: id → set<childId>` both contain EVERY registered id (leaves included: up=-1, down=∅). `m_groupIds: gid → GroupType {Normal, AVSplit, Selection, Leaf}` marks genuine group nodes.

### Decisive source
```cpp
int GroupsModel::getRootId(int id) const
{
    READ_LOCK();
    std::unordered_set<int> seen; // we store visited ids to detect cycles
    int father = -1;
    do {
        Q_ASSERT(m_upLink.count(id) > 0);
        Q_ASSERT(seen.count(id) == 0);
        seen.insert(id);
        father = m_upLink.at(id);
        if (father != -1) id = father;
    } while (father != -1);
    return id;
}
void GroupsModel::setGroup(int id, int groupId, bool changeState)
{
    ...
    removeFromGroup(id);
    m_upLink[id] = groupId;
    if (groupId != -1) {
        m_downLink[groupId].insert(id);
        ... emit GroupedRole change ...
        if (getType(groupId) == GroupType::Leaf) promoteToGroup(groupId, GroupType::Normal);
    }
}
```

**Flow:** create → `createGroupItem` registers the id in BOTH maps (up=-1/down=∅) → link → `setGroup` removes from old parent then relinks and auto-promotes a Leaf-typed target to Normal when it gains its first child → group several items → compute each input's root; if all share ONE root, return that root unchanged instead of creating a singleton group (`roots.size() == 1 && !force` short-circuit) → destroy → `destructGroupItem_lambda` detaches children (`m_upLink[child] = -1`, emits GroupedRole), clears, and downgrades empty nodes. Walks: `getLeaves`/`getSubtree` are BFS over m_downLink collecting childless nodes / all descendants.
**Invariant:** The forest is acyclic by construction and verified defensively — every root walk asserts no revisit; an id missing from either map trips `Q_ASSERT`; group ids come from the same global counter as items.
**Probe:** `tests/groupstest.cpp:27-149` builds a 10-node forest via raw `setGroup` chains and pins literal sets: after `setGroup(0,1), setGroup(1,2), setGroup(3,2)...` → `getLeaves(2) == {0,4,6,7,9}`, `getSubtree(5) == {5,8}`, all of `{0,1,2,3,4,6,7,9}` root at 2; reparenting 3→8 recomputes leaves `{4,6,7,9}` under 5/8.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "GroupsModel subtree walk UP DOWN hierarchy", limit: 30 });
// executed live: rank 1 GroupsModel.getSubtree groupsmodel.cpp:247-263;
// also surfaced copyGroups :716-739, mergeSingleGroups :416-481, split :483-630
```

## Verdict
Adopt the mirrored-maps forest, cycle-detecting root walk, Leaf→Normal auto-promotion, and the single-root short-circuit exactly — they are storage-free algebra. Adapt GroupType enum to your domain (kdenlive's AVSplit/Selection types drive move/trim semantics). Omit toJson/fromJson persistence shapes unless you port project files.
