<!-- capsule-v2 -->
# Snap grid — how do you aggregate snap points from many sources and keep an operation's own edges from snapping to themselves?

**Source:** kdenlive GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL `master@62d6b0b79c51438705ca310b2178f422c1f31fe1`; Codebase Memory `kdenlive`. **Question:** A porter must merge snap candidates from clip edges, markers, subtitles, and the playhead, where several sources can claim the same frame and any source can be temporarily withdrawn mid-operation.

## Refcounted ordered map + ignore/unIgnore bracket
**Path/Symbol:** `src/timeline2/model/snapmodel.cpp:SnapModel` (whole 137L) — addPoint/removePoint (15–32), getClosestPoint (34–52), ignore/unIgnore (81–95), proposeSize (97–137); per-clip projection in `src/timeline2/model/clipsnapmodel.cpp` (12–34, 62–90); interface `SnapInterface` (snapmodel.hpp:15–25).
**Signature:** `void addPoint(int position)` / `void removePoint(int position)` / `int getClosestPoint(int position)` / `void ignore(const std::vector<int> &pts)` / `void unIgnore()` / `int proposeSize(int in, int out, int size, bool right, int maxSnapDist)`.
**Data Shape:** `std::map<int,int> m_snaps` (position → refcount); `m_ignore: std::vector<int>` withdrawal journal. ClipSnapModel keeps its own `unordered_set m_snapPoints` of SOURCE-frame positions plus `m_inPoint/m_outPoint/m_mixPoint/m_position/m_speed`.

### Decisive source
```cpp
int SnapModel::getClosestPoint(int position)
{
    if (m_snaps.empty()) return -1;
    auto it = m_snaps.lower_bound(position);
    long long int prev = INT_MIN, next = INT_MAX;
    if (it != m_snaps.end())  next = (*it).first;
    if (it != m_snaps.begin()) { --it; prev = (*it).first; }
    if (std::llabs(position - prev) < std::llabs(position - next)) return int(prev);
    return int(next);
}
// clipsnapmodel.cpp — speed remap into timeline coordinates
ptr->addPoint(m_speed < 0 ? int(ceil(m_outPoint + m_position + position / m_speed - m_inPoint))
                          : int(ceil(m_position + position / m_speed - m_inPoint)));
```

**Flow:** every clip edge insert/remove adds/removes refcounts on the global model; a frame claimed by k sources survives until k removals → during an operation the caller brackets with `ignore({in,out}) … unIgnore()` so the dragged item's own edges don't attract it → closest point is the nearer lower_bound neighbor within `maxSnapDist`, else no snap → ClipSnapModel registers once (`registerSnapModel(weak_ptr<SnapModel>, pos, in, out, speed)`) and projects each marker through `position/speed` (reversed formula for negative speed, always ceil); move/in-out changes rebuild via removeAllSnaps/addAllSnaps; deregistration withdraws all contributions.
**Invariant:** addPoint/removePoint are exact inverses (Q_ASSERT on removing unknown points); ignore is refcount-aware (double-ignore needs double-unIgnore); empty model answers -1 (never 0).
**Probe:** `tests/snaptest.cpp:10-129` pins all of it literally: double-add then one remove still snaps to 10; double-ignore hides the point until two-level unIgnore; after removing both refs everything returns -1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "kdenlive", query: "snap model closest point ignore proposeSize", limit: 10 });
// executed live: rank 1 SnapModel.ignore :81-87; rank 2 proposeSize :118-137;
// rank 3 getClosestPoint :34-52; also suggestSnapPoint timelinemodel.cpp:6058-6065
```

## Verdict
Adopt the refcounted ordered map, sentinel-based neighbor scan, ignore/unIgnore bracketing, and the ceil-based speed projection formulas verbatim. Adapt SnapInterface's provider set (kdenlive feeds it from markers/subtitles/playhead) to your host's annotation sources. Omit the marker-model back-reference plumbing unless you port bin markers too.
