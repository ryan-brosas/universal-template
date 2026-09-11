---
title: api-design-practices
summary: Use when an existing caller selects this legacy HTTP/JSON API entry; forward to the canonical API owner without introducing a second policy.
kind: playbook
---

# API Design Practices (compatibility entry)

Load `../api-and-interface-design/README.md`. It owns API design decisions and
selects protocol-specific references, including the retained Azure/Google source
capsules. This path stays valid for existing prompts and skills; it introduces
no separate versioning, error, naming, or authorization policy.
