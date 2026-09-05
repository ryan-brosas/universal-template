---
name: api-design-practices
description: "Use when an existing caller selects this legacy HTTP/JSON API entry; forward to the canonical API owner without introducing a second policy."
invocation: manual
disable-model-invocation: true
---

# API Design Practices (compatibility entry)

Load `../api-and-interface-design/SKILL.md`. It owns API design decisions and
selects protocol-specific references, including the retained Azure/Google source
capsules. This path stays valid for existing prompts and skills; it introduces
no separate versioning, error, naming, or authorization policy.
