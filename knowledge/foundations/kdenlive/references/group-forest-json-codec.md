<!-- capsule-v2 -->
# Group-forest JSON codec — how do you serialize a group hierarchy WITHOUT ids and rebuild it in a different track layout at a different offset and fps?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive` (graph surface unavailable this pass — deterministic grep probes below executed byte-for-byte instead). **Question:** A porter must serialize group structure (clipboard, project save) so it can be re-materialized after every item id changed, tracks were remapped, positions shifted, and the fps ratio scaled — with no id table shipped in the payload.

## toJson leaf = "trackPos:pos:subLayer" data string; fromJson re-resolves identity by POSITION; fromJsonWithOffset rewrites leaves through tracksMap + offset + ratio
**Path/Symbol:** `src/timeline2/model/groupsmodel.cpp:GroupsModel::toJson(gid)` (749–771), `toJson()` full forest (779–797), `toJson(roots)` subset (798–806), `fromJson(QJsonObject)` (808–868), `fromJson(QString)` (869–893), `adjustOffset` (894–925), `fromJsonWithOffset` (926–975); position lookups `TimelineModel::getClipByPosition` (465–473), `getClipByStartPosition` (458–462), `getSubtitleByStartPosition` (483+), `TrackModel::getClipByPosition` mix-aware (856–882), `getClipByStartPosition` linear scan (845–853).
**Signature:** `QJsonObject toJson(int gid) const`; `const QString toJson(const std::unordered_set<int> &roots) const`; `int fromJson(const QJsonObject &o, Fun &undo, Fun &redo)`; `bool fromJsonWithOffset(const QString &data, const QMap<int,int> &trackMap, int offset, double ratio, Fun &undo, Fun &redo)`.
**Data Shape:** leaf JSON = `{"type":"Leaf","leaf":"clip|composition|subtitle","data":"<trackPos>:<pos>:<subLayer>"}` (subtitle leaves use trackPos **-2** and carry the layer in slot 3); group JSON = `{"type":"AVSplit|Normal|...","children":[...]}`. No ids anywhere — identity is (kind, track position, start frame).

### Decisive source
```cpp
// groupsmodel.cpp:760-770 — serialization: position-keyed leaf identity, no ids
currentGroup.insert(QLatin1String("leaf"),
    QJsonValue(QLatin1String(ptr->isClip(gid) ? "clip" : ptr->isComposition(gid) ? "composition" : "subtitle")));
int track = ptr->isSubTitle(gid) ? -2 : ptr->getTrackPosition(ptr->getItemTrackId(gid));
int pos = ptr->getItemPosition(gid);
int subLayer = ptr->isSubTitle(gid) ? ptr->getSubtitleLayer(gid) : -1;
currentGroup.insert(QLatin1String("data"), QJsonValue(QStringLiteral("%1:%2:%3").arg(track).arg(pos).arg(subLayer)));
```
```cpp
// groupsmodel.cpp:830-846 — deserialization: resolve the leaf back by kind + position
int trackPos = data.section(":", 0, 0).toInt();
int trackId = trackPos > -1 ? ptr->getTrackIndexFromPosition(trackPos) : -1;
int pos = data.section(":", 1, 1).toInt();
int subLayer = trackId == -2 ? data.section(":", 2, 2).toInt() : -1;
if (leaf == QLatin1String("clip")) {
    id = ptr->getClipByStartPosition(trackId, pos);
} else if (leaf == QLatin1String("composition")) {
    id = ptr->getCompositionByPosition(trackId, pos);
} else if (leaf == QLatin1String("subtitle")) {
    id = ptr->getSubtitleByStartPosition(subLayer, pos);
}
...
if (ids.count(-1) > 0 || type == GroupType::Selection) { return -1; }   // any unresolved leaf kills the group
return groupItems(ids, undo, redo, type);
```
```cpp
// groupsmodel.cpp:894-918 — the paste-time leaf rewrite: trackMap + offset + ratio applied to data strings
QString cur_data = child.value(QLatin1String("data")).toString();
int trackId = cur_data.section(":", 0, 0).toInt();
int pos = cur_data.section(":", 1, 1).toInt() * ratio;                 // fps-ratio scaling
int trackPos = trackId == -2 ? -2 : ptr->getTrackPosition(trackMap.value(trackId));  // track remap
int subLayer = trackId == -2 ? cur_data.section(":", 2, 2).toInt() : -1;
pos += offset;                                                          // paste offset
child.insert(QLatin1String("data"), QJsonValue(QStringLiteral("%1:%2:%3").arg(trackPos).arg(pos).arg(subLayer)));
```

**Flow:** (1) SERIALIZE: walk each root recursively; group nodes emit type + children; leaves emit kind + a `trackPos:pos:subLayer` string where trackPos is the track's POSITION (not id) and subtitles use the -2 sentinel with the layer in slot 3; the full-forest `toJson()` demotes Selection roots to their child groups (selection is never serialized); the subset `toJson(roots)` (used by copyClips) skips Selection roots entirely; (2) REWRITE (paste path only): `fromJsonWithOffset` first runs `adjustOffset` over every leaf, replacing the data string's track through `tracksMap` (source track id → target track id, then id→position), scaling pos by the fps ratio, and adding the paste offset — the rewritten tree is then fed to the ordinary `fromJson`; (3) REBUILD: `fromJson` recurses; leaves resolve through `getClipByStartPosition`/`getCompositionByPosition`/`getSubtitleByStartPosition` (position-derived identity — the items must already exist, which is why paste inserts ALL clips before rebuilding groups); any unresolved leaf (-1) or Selection type aborts that group; resolved children are joined with `groupItems(..., type)` preserving the group type; the whole rebuild rides the caller's accumulators.
**Invariant:** the payload contains NO ids — identity is (kind, track position, start frame), so the same payload re-materializes against any layout; group reconstruction happens strictly AFTER all items exist; a single unresolvable leaf fails its whole group (never a partial group); Selection groups are never serialized; the mix-aware `getClipByPosition(playlist=-1)` disambiguation (returning the mix partner when the probe lands inside a mix overlap) is what keeps leaf resolution correct for clips under same-track mixes.
**Probe:** `tests/groupstest.cpp:534-660` "Basic Creation and export/import from json": `fromJson(toJson())` round-trip across TWO different timelines; a recursive `rec_check` verifier walks the imported forest and asserts every imported group maps to exactly one original group via the unique-parent property; both timelines `checkConsistency` green after import. Paste-path integration pinned by `tests/trimmingtest.cpp:968-1321` "Copy/paste" (AVSplit pair pasted recreates the AVSplit group).

## Get live surrounding code
**Retrieve:**
```bash
$ grep -n 'toJson\|fromJson\|adjustOffset' src/timeline2/model/groupsmodel.cpp
749:QJsonObject GroupsModel::toJson(int gid) const
779:const QString GroupsModel::toJson() const
798:const QString GroupsModel::toJson(const std::unordered_set<int> &roots) const
808:int GroupsModel::fromJson(const QJsonObject &o, Fun &undo, Fun &redo)
869:bool GroupsModel::fromJson(const QString &data)
894:void GroupsModel::adjustOffset(QJsonArray &updatedNodes, const QJsonObject &childObject, int offset, const QMap<int, int> &trackMap, double ratio)
926:bool GroupsModel::fromJsonWithOffset(const QString &data, const QMap<int, int> &trackMap, int offset, double ratio, Fun &undo, Fun &redo)
$ grep -n 'fromJsonWithOffset' src/timeline2/model/timelinefunctions.cpp
2869:        timeline->m_groups->fromJsonWithOffset(groupsData, tracksMap, position - offset, ratio, timeline_undo, timeline_redo);
# executed live this pass; graph search_graph unavailable (MCP not connected in session)
```

## Verdict
Adopt position-keyed identity for any "duplicate a scene" serialization: store (kind, lane position, start frame) per leaf, never ids, and resolve by lookup at rebuild time — this is what makes the payload portable across layouts, documents, and fps changes. Adopt the rewrite-before-parse shape (`adjustOffset` transforms data strings, then the plain parser runs unchanged). Adopt fail-the-whole-group on any unresolved leaf. Adapt the data-string encoding to structured JSON fields if you prefer (kdenlive's "a:b:c" string is a compact legacy choice); adapt the -2 subtitle sentinel to your overlay model. Omit the Selection-root demotion if your host has no transient selection groups. Porting risk: position-keyed resolution silently re-binds if two items share a start frame on one lane — kdenlive tolerates this because the model forbids overlap; a host that allows zero-length or stacked items needs a tiebreaker.
