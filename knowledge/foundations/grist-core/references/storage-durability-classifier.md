<!-- capsule-v2 -->
# Storage durability classification — how do you decide at boot whether your data directory survives restarts, before trusting it?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How can a containerized server detect that its data path is a RAM disk (or an unmounted throwaway layer) and warn/act BEFORE user data is written into it?

## Mount-table longest-prefix classifier with three-valued result
**Path/Symbol:** `app/server/lib/storageDurability.ts:classifyStorage` (:19–31), `readMounts` (:40–54), `mountFor` (:58–67); consumed by `app/server/lib/BootProbes.ts:471–472`.
**Signature:** `async classifyStorage(target: string | undefined, rootMayBeEphemeral: boolean): Promise<Durability>` where `type Durability = "durable" | "ephemeral" | "unknown"`.
**Data Shape:** Parses `/proc/self/mountinfo` lines (`ID PID MAJ:MIN ROOT MOUNTPOINT OPTS [TAGS...] - FSTYPE SOURCE SUPEROPTS`) into `{mountPoint, fsType}`; RAM set = {tmpfs, ramfs}.

### Decisive source
```ts
export async function classifyStorage(
  target: string | undefined, rootMayBeEphemeral: boolean,
): Promise<Durability> {
  if (!target) { return "unknown"; }
  const mounts = await readMounts();
  if (!mounts) { return "unknown"; }
  const root = mountFor("/", mounts);
  const mount = mountFor(target, mounts);
  if (!root || !mount) { return "unknown"; }
  if (RAM_FILESYSTEMS.has(mount.fsType)) { return "ephemeral"; }
  // Target shares the ROOT mount: nothing is mounted there — ephemeral only
  // if the root itself may be a throwaway container layer.
  if (mount.mountPoint === root.mountPoint) {
    return rootMayBeEphemeral ? "ephemeral" : "unknown";
  }
  return "durable";   // any dedicated mount is assumed durable
}
// Longest-prefix match, pure string logic — works even if target doesn't exist yet.
function mountFor(target: string, mounts: MountInfo[]): MountInfo | undefined {
  const p = path.resolve(target);
  let best: MountInfo | undefined;
  for (const mount of mounts) {
    const within = mount.mountPoint === "/" || p === mount.mountPoint ||
      p.startsWith(mountPoint + "/");
    if (within && (!best || mountPoint.length > best.mountPoint.length)) best = mount;
  }
  return best;
}
```

**Flow:** no target / unreadable `/proc/self/mountinfo` → `"unknown"` → resolve target's owning mount by LONGEST-PREFIX string match → tmpfs/ramfs ⇒ `"ephemeral"` → same mount as `/` ⇒ `"ephemeral"` only when the caller asserts the root may be a container layer, else `"unknown"` → anything else (a real volume mounted at/below target) ⇒ `"durable"`.
**Invariant:** Classification is pure string prefix logic over the mount table — it never touches the target path itself, so it answers correctly for directories that do not yet exist; "unknown" is distinct from "durable" and consumers must treat it as not-proven. Linux-only by construction (/proc) — the port must keep the honest third state rather than defaulting to durable.
**Probe:** No direct unit test pins `classifyStorage`; consumed by BootProbes' persist-data probe (test/server/lib/BootProbes.ts exercises the probe surface, not this helper's branches). Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "classifyStorage storageDurability BootProbes persist", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any self-hosted/container product that writes local state: run the classifier in boot probes and refuse-or-warn on ephemeral data paths. Adapt the fs-type denylist (add zram; Windows would need a different source entirely) and the root-ephemeral policy flag. Omit the root-mount special case if your deployment always mounts a data volume.
