---
title: authoritative-signal-surfacing
summary: 'Use when a host, harness, or backend signal (notification, status line, badge, transcript annotation) must appear in a derived UI view, or when one shows on the wrong surface or the wrong position; decide the surface from the producer, anchor placement to identity or tail, and prove presence plus absence in the built app.'
kind: playbook
---

# Surface an authoritative signal in a derived view

A derived view that rebuilds from an authoritative stream (RPC transcript, log,
event feed) makes surfacing a decision, not a side effect: the producer owns what
the signal means, the view owns where it appears, and the view can be rebuilt at
any moment. Three decisions cause rework in practice.

## 1. Take the surface from the producer

Read the producer's own kind/severity-to-surface mapping in the pinned source and
cite it. Hosts routinely distinguish contracts that look alike:

- a **transcript or console status line** is scoped to the unit of work, usually
  rewrites the previous line when the same unit reports twice, and disappears
  with the stream;
- a **notification stack** is durable, dismissible, badged, and often ledgered.

Sending informational telemetry to the durable stack pushes a readout nobody must
act on into an attention surface. Moving a signal across that line changes
durability, dismissal and unread behavior: check each of those, and make the value
reset with the stream it belongs to.

## 2. Mirror the producer's presentation semantics

Copy the semantics the producer already fixed rather than inventing a parallel convention:
replace-versus-append for repeated reports, placement relative to the unit of work
(turn, request, task), and what counts as the same previous entry.

## 3. Anchor placement to identity or tail, never to window position

The view rebuilds from a paginated stream, so a position captured as an index or
offset drifts as soon as history is prepended, the stream is replaced, or the
signal arrives before the stream loads (resume, reconnect, session restore).

- Anchor to a stable identity when the producer supplies one and resolve it at
  render time; fall back to a tail anchor when the anchor is outside the loaded window.
- Prefer the tail when the signal arrives before the stream loads: in an
  append-only producer that line would have been appended to whatever was there,
  not to the first unit of history.
- Make placement **total**. An anchor that resolves outside the loaded window must
  still render (at the tail); silently dropping an annotation is worse than
  placing it approximately.
- Keep **one** anchor convention per view family. When an existing mechanism
  already computes the position, share that helper instead of adding a second numbering.
- Audit both directions: every path that **replaces** the stream (switch, clone,
  fork, navigation, new session) must reset the annotation scope, and every path
  that **extends** it (paging prepend) must not shift existing annotations.

## Boundaries

The authority stays authoritative: this is not a license to keep a second copy of
producer state or a parallel loop. Visual polish belongs to design-pack, gate
evidence to [false-green-gates](../false-green-gates/README.md), and verifying
producer behavior from its own source to
[source-driven-development](../source-driven-development/README.md).

## Verification

In the real built app the signal appears on the intended surface **and** the wrong
surface does not carry it — assert both, because presence alone still passes when
the signal has merely been duplicated. Keep that assertion in the tracked gate
rather than a scratch script. Cover the boundaries: arrival before the stream
loads, anchor outside the loaded window, paging prepend, stream replacement.
