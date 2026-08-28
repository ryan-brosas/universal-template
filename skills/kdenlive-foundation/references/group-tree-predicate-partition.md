<!-- capsule-v2 -->
# Group-tree predicate partition — how do you split a group tree by a predicate without corrupting the live forest: the temp-negative-id copy, prune, and bottom-up rebuild kernel?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must partition a group hierarchy into "keep" and "move" halves by a per-leaf predicate (e.g. position < cut point), preserving each group node's type (AVSplit, Normal, …), without ever leaving the live forest in an inconsistent intermediate state, and as one undoable step.

## GroupsModel::split: BFS copy with temp ids → simulate deletion → recreate leaves → prune → rebuild bottom-up
**Path/Symbol:** `src/timeline2/model/groupsmodel.cpp:GroupsModel::split` (483–633); helpers `destructGroupItem` (156–186), `groupItems`, `mergeSingleGroups` (416–474), `setInGroupOf` (627–639).
**Signature:** `bool split(int id, const std::function<bool(int)> &criterion, Fun &undo, Fun &redo)`.
**Data Shape:** `id` must be a ROOT (`Q_ASSERT(m_upLink[id] == -1)`) and not a Selection group; `corresp` maps real id → temporary NEGATIVE id (counting down from -10); `to_move` = leaves satisfying the criterion; `new_groups` = temp-group-id → set of children (real leaf ids or temp ids); `new_types` = temp-group-id → GroupType.

### Decisive source
```cpp
// groupsmodel.cpp:494-524 — phase 1: BFS the subtree, building a SHADOW copy with temp negative ids
std::unordered_map<int, int> corresp;   // real id -> temp negative id
corresp[-1] = -1;                       // root sentinel maps to itself
std::vector<int> to_move;
std::unordered_map<int, std::unordered_set<int>> new_groups;
std::unordered_map<int, GroupType> new_types;
std::queue<int> queue; queue.push(id);
int tempId = -10;
while (!queue.empty()) {
    int current = queue.front(); queue.pop();
    if (!isLeaf(current) || criterion(current)) {
        if (isLeaf(current)) {
            to_move.push_back(current);
            new_groups[corresp[m_upLink[current]]].insert(current);   // leaf joins its shadow parent
        } else {
            corresp[current] = tempId;
            new_types[tempId] = getType(current);                     // GroupType preserved
            if (m_upLink[current] != -1) new_groups[corresp[m_upLink[current]]].insert(tempId);
            tempId--;
        }
    }
    for (const int &child : m_downLink.at(current)) queue.push(child);
}
```
```cpp
// groupsmodel.cpp:526-548 — phase 2: simulate deletion, then recreate the leaves as free roots
for (const auto &leaf : to_move) {
    destructGroupItem(leaf, true, undo, redo);    // detach from old tree (undoable)
}
Fun operation = [this, to_move]() { for (const auto &leaf : to_move) createGroupItem(leaf); return true; };
Fun reverse  = [this, to_move]() { for (const auto &group : to_move) destructGroupItem(group); return true; };
bool res = operation();
UPDATE_UNDO_REDO(operation, reverse, undo, redo);
```
```cpp
// groupsmodel.cpp:550-605 — phase 3: prune empty shadow groups, then rebuild bottom-up
// prune loop: erase any new_groups entry with no children OR whose children reference erased temps
// rebuild loop: pick any shadow group whose children are all real leaves or already-created temps
while (!new_groups.empty()) {
    int selected = INT_MAX;
    for (const auto &group : new_groups) {
        bool ok = true;
        for (int elem : group.second) {
            if (elem < -1 && created_id.count(elem) == 0) { ok = false; break; }
        }
        if (ok) { selected = group.first; break; }
    }
    Q_ASSERT(selected != INT_MAX);
    std::unordered_set<int> group;
    for (int elem : new_groups[selected]) group.insert(elem < -1 ? created_id[elem] : elem);
    int gid = groupItems(group, undo, redo, new_types[selected], true);   // REAL ids, type preserved
    created_id[selected] = gid;
    new_groups.erase(selected);
}
if (regroup) {
    if (m_groupIds.count(id) > 0) mergeSingleGroups(id, undo, redo);              // collapse singletons
    if (created_id[corresp[id]]) mergeSingleGroups(created_id[corresp[id]], undo, redo);
}
Fun clear_group_selection = [this, newGroups]() {
    if (auto ptr = m_parent.lock()) ptr->clearGroupSelectionOnDelete(newGroups);
    return true;
};
PUSH_FRONT_LAMBDA(clear_group_selection, undo);   // selection hygiene PREPENDED to undo
```

**Flow:** (1) BFS the root's subtree; every leaf satisfying `criterion` is collected into `to_move`; every group node on the path gets a shadow temp id with its GroupType recorded; (2) each moved leaf is destructed out of the OLD tree (undoable, orphan-group cleanup via `deleteOrphan=true`), then immediately recreated as a free root — the old tree is now consistent without the moved half; (3) the shadow `new_groups` map is pruned: any temp group left with no children, or whose children all point to erased temp groups, is erased (repeat until stable); (4) the new tree is rebuilt BOTTOM-UP: repeatedly pick a shadow group whose children are all available (real leaves or already-materialized temp groups), call `groupItems` with the recorded GroupType, and record temp→real in `created_id`; (5) `mergeSingleGroups` collapses singleton wrappers on BOTH surviving roots; (6) a selection-cleanup lambda is PREPENDED to undo so a stale selection referencing a deleted group node cannot survive an undo. The criterion is only ever evaluated on LEAF ids (the caller's lambda reads item positions), and the split is refused entirely when a Selection group is active (`regroup=false` guard via the assert).
**Invariant:** the live forest is never inconsistent: phase 2 leaves the old tree valid (moved leaves detached then re-rooted), and phase 4 creates the new tree bottom-up so every `groupItems` call sees only existing ids; GroupType is carried through `new_types` so AVSplit wrappers survive the partition; the whole operation rides the caller's `undo/redo` accumulators — one undo step for the entire partition.
**Probe:** `tests/trimmingtest.cpp:444-531` "Cut should preserve AV groups": after cutting an AV pair, BOTH halves end in their own `GroupType::AVSplit` groups with exactly the two clip children each — the type-preserving bottom-up rebuild pinned end-to-end; undo restores the pre-cut forest, redo reproduces it. `tests/groupstest.cpp:20-149` pins the forest algebra `split` builds on (setGroup/reparent/roots).

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'corresp\|tempId\|new_groups\|mergeSingleGroups' src/timeline2/model/groupsmodel.cpp | head -14
416:bool GroupsModel::mergeSingleGroups(int id, Fun &undo, Fun &redo)
495:    std::unordered_map<int, int> corresp; // keys are id in the original tree, values are temporary negative id assigned for creation of the new tree
496:    corresp[-1] = -1;
501:    std::unordered_map<int, std::unordered_set<int>> new_groups;
506:    int tempId = -10;
513:                new_groups[corresp[m_upLink[current]]].insert(current);
515:                corresp[current] = tempId;
516:                new_types[tempId] = getType(current);
517:                if (m_upLink[current] != -1) new_groups[corresp[m_upLink[current]]].insert(tempId);
518:                tempId--;
550:    // We prune the new_groups to remove empty ones
562:                if (it2 < -1 && new_groups.count(it2) == 0) {
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt the three-phase kernel verbatim for ANY "partition this tree by predicate" operation: shadow-copy with temp ids (types recorded) → detach-and-re-root the moved leaves → prune empty shadow groups → rebuild bottom-up with real ids. Adopt temp NEGATIVE ids for shadow nodes — they cannot collide with the real id space and their sign doubles as a "not yet materialized" flag. Adopt the prepend-selection-cleanup-to-undo hygiene. Adapt the criterion domain (kdenlive evaluates it on leaf ids via a timeline lookup; a pure-tree port would pass leaf payloads). Omit `mergeSingleGroups` if your forest has no singleton-wrapper concept. Porting risk: the prune loop is O(n²) in pathological deep trees — fine for editor-scale forests, re-derive it if you port to huge hierarchies.
