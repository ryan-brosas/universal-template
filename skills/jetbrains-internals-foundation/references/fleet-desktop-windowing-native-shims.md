<!-- capsule-v2 -->
# fleet-desktop-windowing-native-shims — which native libraries ride the installer, and how is each one's integrity pinned?

**Source:** JetBrains installed distributions (proprietary) air build `262.132.35`, pin `?@?`. Codebase Memory `jetbrains-air`. **Question:** What do `lib/app/libs/*.so` actually provide, and what provenance/integrity contract covers them?

## Two windowing backends behind one C ABI + a checksummed Skia
**Path/Symbol:** `lib/app/libs/`: `libdesktop_linux_x64.so` (5,990,064 B), `libdesktop_gtk_x64.so` (1,408,760 B), `+debug` twins for both, `libjnidispatch.so` (134,447 B), `libskiko-linux-x64.so` (29,619,352 B) + `libskiko-linux-x64.so.sha256` sidecar (64 B).
**Signature:** all ELF 64-bit shared objects; libdesktop pair exports a flat C ABI: 21 `application_*` functions (`application_init`, `application_clipboard_{get_available_mimetypes,paste,put}`, `application_close_notification`, `application_get_egl_proc_func`, `application_is_event_loop_thread`, `application_open_file_manager`, …).

### Decisive source
\`\`\`text
$ echo "$(cat libskiko-linux-x64.so.sha256)  libskiko-linux-x64.so" | sha256sum -c -
libskiko-linux-x64.so: OK                       # sidecar = bare hex digest, verified GREEN
$ ldd libdesktop_linux_x64.so | awk '{print $1}' | tr '
' ' '
linux-vdso libxkbcommon.so.0 libwayland-egl.so.1 libwayland-client.so.0 libgcc_s libm libc ld-linux libffi.so.8
$ ldd libdesktop_gtk_x64.so | awk '{print $1}' | head -14
linux-vdso libglib-2.0 libgtk-4.so.1 libpango-1.0 libgraphene-1.0 libgio-2.0 libgobject-2.0 … libcairo.so.2
$ nm -D --defined-only libdesktop_linux_x64.so | grep -c " T application_"
21
$ cmp ../../libs/libjnidispatch.so <(unpacked jetbrainsd/bin/libjnidispatch.so) → IDENTICAL
# skiko identity: harfbuzz (hb_unicode_compose/decompose) + ICU LSTM line-breaking *_skiko symbols
# catalog cross-ref: grep skiko/jnidispatch across bootstrap/*.json + code-cache/*/parts.json → ZERO hits
\`\`\`

**Flow:** dock/desktop app loads ONE windowing shim by session type — Wayland sessions take the direct `linux` variant (xkbcommon + wayland-{egl,client} only), X11/GTK paths take the `gtk` variant (full GTK4 stack hard-linked); both expose the identical `application_*` C ABI so the JVM side needs no backend branching; Compose rendering goes through skiko (Skia + harfbuzz shaping), whose ONLY integrity pin is the bare-hex `.sha256` sidecar; jnidispatch (JNA) ships byte-identical in TWO places (libs/ and inside the jetbrainsd seed tarball) — one artifact, two consumers.
**Invariant:** none of these libraries is referenced by the signed bundle catalog or parts.json manifests — provenance is the INSTALLER, not the catalog; integrity rests on (a) the skiko sidecar digest and (b) build-time equality of duplicated artifacts. The `+debug` twins are dev payloads shipped alongside release, not loaded by default.
**Probe:** \`nm -D --defined-only libdesktop_linux_x64.so | grep -c " T application_"\` → \`21\`; \`sha256sum -c libskiko-linux-x64.so.sha256\` (with filename-formatted line) → OK.
**Retrieve:** negative retrieval recorded:
\`\`\`ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-air", paths: ["lib/app/libs/libskiko-linux-x64.so", "lib/app/libs/libdesktop_gtk_x64.so"] });
// both → status excluded / kind not_indexed_file / detail ignored-suffix ; .sha256 sidecar → no_recorded_issue/not_tracked
\`\`\`

## Verdict
Adopt: ship windowing diversity as SAME-C-ABI variant shims selected by display-server session; pin every renderer blob with a bare-hex sidecar next to it; treat installer-bundled natives as OUTSIDE your signed-package manifest but still verify them. Adapt backend pairs to your platform set (this install: wayland-direct vs gtk4). Omit skiko/JNA internals and the debug twins' symbols (upstream projects). Coverage caveat: whole directory is ignored-suffix in the graph; claims rest on executed ldd/nm/sha256 probes.
