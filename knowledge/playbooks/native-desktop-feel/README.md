---
title: native-desktop-feel
summary: "Use when a native desktop app does not feel adopted, optimized, or native on Linux or another OS flavor, especially with a .desktop file or distro name attached; decide lag versus flavor, and whether a Linux-motivated fix belongs in a platform seam or in shared product code."
kind: playbook
---

# Native desktop feel

“Doesn’t feel native/adopted/optimized” on a desktop OS or flavor is ambiguous.
A `.desktop` file, installer path, or distro name in context is often **how the
user launches the app**, not a request to implement theming, DE plugins, or
flavor-specific chrome.

## Decision

Pick one complaint with cheap evidence. Ask only if that evidence is missing.

| Complaint | Cheap evidence | Next |
|---|---|---|
| **Lag / jank** | Hitching on input or streaming, high process CPU while using the app, an existing perf audit | [performance-optimization](../performance-optimization/README.md) |
| **Clicks miss padding, or wheel dies after a hit-target fix** | Only glyphs respond; list no longer scrolls | [gpuix-hit-testing](../gpuix-hit-testing/README.md) |
| **Open/Save does nothing, or `dbus-monitor` leaks** | No chooser window; a validated application PID has a lingering `dbus-monitor` Request.Response child | [xdg-portal-cli](../xdg-portal-cli/README.md) |
| **Missing identity** | No launcher icon, wrong `app_id` / `StartupWMClass`, window does not group | Packaging / desktop-entry work |
| **Flavor feature** | Explicit ask for theme follow, appearance portals, DE settings | That feature, not a feel program |

Do not start an Omarchy/GNOME/KDE “adoption” program (palette overlay, extra
providers, distro coupling) unless the user asked for that feature. The desktop
environment can be the **acceptance machine** without becoming a product
dependency.

**Support is not a second app and not an `if (linux)` around a product
invariant.** A `.desktop` complaint can still be a bug in the one workbench
controller. Gate only platform facts (launcher, `app_id`, decorations, XDG
last-workspace, FileChooser portal). Keep shared invariants (do not abort a turn on switch; do not
steal the list wheel) in the owning module — hiding them behind Linux would
re-break other platforms. Re-land backup/Linux branches **per concern**; do not
fork the product for Omarchy.

## If the complaint is lag

1. Inspect the **installed or running binary**, not only source. A desktop
   launcher may run a copied preview; an existing process can retain the previous
   image after a build or install. A development watcher does not prove the
   preview is current. Prove which image a validated PID executes before
   rebuilding:
   [runtime-artifact-provenance](../runtime-artifact-provenance/README.md).
2. Inventory **already-shipped** optimizations versus remaining measured
   bottlenecks. Re-land a proven slice **per concern**. Do not merge a backup
   branch wholesale because it once contained Linux work.
3. For recurring native polls, streaming, or JS↔UI-thread calls, build the
   [cross-boundary work budget](../performance-optimization/references/recurring-cross-boundary-work.md)
   before adding platform APIs. App-level ownership, cadence, and object-identity
   reuse come first; a runtime pin change is later.
4. Dogfood through the **same launcher** the user uses. If the installed or loaded
   artifact is stale, follow the provenance playbook's authorized activation flow.
5. Inventory **children of the validated application PID**. A lingering
   `dbus-monitor` with no dialog warrants checking the request lifecycle and
   response matcher, not assuming “the button is laggy.”

## Boundaries

- An explicit theme, portal, or packaging request skips this disambiguation.
- Once lag is the complaint, still measure; this playbook does not pick the
  bottleneck.
- Visual design of a new desktop UI belongs to design-pack.

## Verification

The work matches the disambiguated complaint. For lag, the user-facing launcher
runs the new artifact and a named metric or profile moved, not “it should feel
faster.”
