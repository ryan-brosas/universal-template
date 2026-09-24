---
title: xdg-portal-cli
summary: "Use when a Linux desktop app's Open/Save folder dialog is missing, hangs, or leaves dbus-monitor running; drive FileChooser via gdbus, listen for Response before OpenFile, and match unquoted dbus-monitor paths."
kind: playbook
---

# XDG portal from CLI

A non-GTK app can call `org.freedesktop.portal.FileChooser` with gdbus.
The dialog is asynchronous. The Hyprland failure mode is a leaked
`dbus-monitor` and a false second dialog: either the Response never
matches, or cancel falls through to zenity.

## Decision

| What you observe | Do this |
|---|---|
| Portal service active, zenity missing | Portal first, then kdialog, then zenity |
| User cancelled the portal | Stop. Do not open a CLI fallback |
| Lingering `dbus-monitor` child of the validated application PID, no chooser window | Inspect the request lifecycle and emitted Response; check for a matcher miss |

Do not take a GPUIX/native D-Bus pin just to get a folder picker.

## Sequence

1. Subscribe to `Request.Response` **before** `OpenFile`. Fast cancel can
   otherwise arrive unseen.
2. Pass a unique `handle_token`. The request object path ends with it.
3. Match the live dbus-monitor line, often **unquoted**:
   `path=/org/freedesktop/portal/desktop/request/<sender>/<token>;`
   Quoted `path='/org/...'` is not the Hyprland default. Require the token
   and a `uint32` response code before treating the stream as complete.
4. Kill the monitor on parse, abort, and OpenFile failure. A long timeout
   is not a matcher.
5. `uint32 1` is cancel. Degrade to CLI pickers only when the portal is
   **unavailable**.

## Boundaries

- Omarchy palettes and `org.freedesktop.appearance` stay flavor work in
  [native-desktop-feel](../native-desktop-feel/README.md).
- Parent-window / modal attach needs a native pin; empty parent is the
  CLI support slice.
- HTML file inputs and GTK choosers are different stacks.

## Verification

Cancel does not spawn zenity. After a selection, no `dbus-monitor` remains
under the validated application PID. Tests inject unquoted dbus-monitor
fixtures, not only quoted gdbus objectpaths.
