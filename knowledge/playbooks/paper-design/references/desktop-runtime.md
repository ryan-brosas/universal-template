# Paper desktop updates, startup and scaling

Use this for Paper Desktop maintenance, especially Linux AppImages and a changed
interface size after an update or launch workaround. It is not a design-editing
workflow. Use the installed desktop skill for OS/compositor actions; this reference
does not replace vendor instructions or authorize global desktop changes.

## Update the installation the user actually launches

Resolve the desktop entry to the installed app and running process, and locate its
active profile before choosing an update method. Packaged apps, mounted AppImages
and extracted AppImages have different activation paths. Use engineering-pack's
[runtime artifact provenance](../../runtime-artifact-provenance/README.md) when
installed and loaded identities disagree; an archive's version alone does not
prove the open window runs it.

For a manually maintained extracted AppImage:

1. Inspect the installed updater metadata, such as `resources/app-update.yml`,
   and use its vendor release feed. Stage the matching OS/architecture artifact
   and check the published size and checksum before replacing the installation.
   Do not retain a session's release URL, version or hash as a permanent latest pin.
2. Confirm saved work and restart permission. Re-identify the current window/PID
   and workspace after a delay; the user may have continued editing. Request a
   graceful close and await that instance's remaining processes before copying its
   profile. If Paper stays open, inspect the reason rather than force-killing it.
   Verify current dispatcher syntax: Lua-based Hyprland does not accept every old
   dispatcher argument form.
3. Preserve the old app, archive and launcher; privately copy and verify the stopped
   profile. It contains designs and session data. Keep the active profile in place
   during the update. Restoring an old profile is a separate, potentially lossy
   action, not an automatic part of binary rollback.
4. Replace the intended installation, validate the existing launcher and restart
   on its prior workspace without taking focus. Keep logs and rollback paths
   private. Do not assume an extracted installation's automatic updater is active;
   check the installed version's startup evidence.

## Argument-sensitive AppRun

Inspect the shipped `AppRun` before adding flags or repairing `paper://` handling.
An observed launcher derived `APPDIR` by searching parent directories for `$1`.
It worked with no arguments, but a flag made the search empty and execution failed
with `/paper-desktop: No such file or directory`. That is a launcher failure,
not evidence that Paper's executable is missing or its profile is corrupt.

For a script with this behavior, supply its actual AppDir explicitly in the user
launcher rather than patching vendor files:

```ini
Exec=env APPDIR=/absolute/path/to/AppDir /absolute/path/to/AppDir/AppRun %U
```

Replace both placeholders with the installed directory; desktop entries do not
perform shell-variable expansion. Preserve URI forwarding and unrelated launcher
fields. Check arguments as well as a no-argument start: a successful plain launch
does not exercise the failing branch. Do not generalize this script's behavior to
all AppImages or reinstall a protocol integrator before inspecting the launcher.

## A graphics warning is not a crash verdict

A Wayland/Vulkan diagnostic, a missing result from an old window-class filter, and
an actual process exit are different evidence. Revalidate the exact PID and window;
a release or backend change can change the class. If the process exited, inspect
its shutdown/exit evidence and any core dump rather than inventing a cause.

Preserve the existing native backend when it works. For compatibility diagnosis,
reproduce the affected behavior before comparing backends; a warning alone is not
a reason to switch. Keep the experiment scoped to Paper. A backend workaround
that opens the app but enlarges its interface is a regression, not completion.
Do not disable sandboxing or change global font/monitor settings to conceal it.

## Separate interface scaling from canvas zoom

“Zoomed out” may mean small artwork, small controls, or simply that the view feels
wrong. Establish which direction and which surface changed: menus/sidebar versus
the design canvas. Use visible evidence or a short clarification before choosing
a correction; absence of a saved browser zoom preference does not prove either
surface is at its default scale.

Check Paper's current monitor, that monitor's scale, the actual Wayland/XWayland
backend, and any relevant app/X11 scaling overrides. Do not infer its scale from
the primary display alone. On Hyprland, window metadata's `xwayland: false`
confirms native Wayland, but does not by itself prove that the UI looks right.

When the regression followed a forced `--ozone-platform=x11`, removing that
recent override and testing native Wayland is a useful controlled comparison.
Retain needed launcher fixes such as explicit `APPDIR`; leave desktop-wide scale,
canvas geometry and unrelated settings alone. Get fresh restart permission if the
user has resumed work. Native Wayland is not a universal cure: inspect the result
before retaining or rejecting either backend.

## Verify the restart

Check the loaded release, a mapped window on the expected workspace/monitor, and
the intended backend. Then use the existing connection's read-only
[`get_basic_info` context check](mcp-and-handoff.md#establish-file-and-page-context)
to confirm the prior file/page reopened. Tool discovery, a PID or a listening port
alone does not establish a working editor; no design mutation is needed for this
check. If no file was open, report that limit rather than creating a test design.

A successful MCP call with a failed local parser is not an app startup failure.
For Fabric's structured or mixed-text response handling, use the agent-tooling
owner's [result-handling guidance](../../fabric-native-execution/README.md#after-a-rejected-program)
instead of repeating the operation to repair parsing.

Finally verify the reported visual problem: inspect the interface or obtain the
user's confirmation that its size is normal. Keep that result separate from
successful startup and document reads. Record the retained launcher change and
rollback location without publishing profiles, design identifiers or host-specific
recovery logs.
