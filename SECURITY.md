# Security Policy

## Reporting a vulnerability

Use GitHub private vulnerability reporting: Security tab, "Report a
vulnerability". Private reporting is enabled for this repository; reports stay
private until a fix ships.

Please do not open a public issue for anything exploitable.

## Scope

This repository is a configuration and skill catalog: Python gate scripts and
shell snippets run locally, GitHub Actions workflows run in CI. Findings about
workflow injection, secret exposure, private machine identifiers,
unsafe host-config mutation, browser recording disclosure, or injection through
gate scripts are in scope. The publication gate scans Git-tracked text for
credential patterns and rejects tracked runtime/session artifacts; report any
false negative privately.

## Supported versions

Use the latest tagged release (`vX.Y.Z`); fixes land on `main` first.
