<!-- capsule-v2 -->
# Vendor override plane — how do you patch composer dependencies without forking them?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How does the app replace vendor class implementations (Swiftmailer transports, Symfony console, webklex/php-imap) with edited copies that still autoload?

## overrides/ shadow tree
**Path/Symbol:** repo root `overrides/` — mirrors vendor FQCN paths: `overrides/swiftmailer/swiftmailer/lib/classes/Swift/Transport/*.php`, `overrides/symfony/console/Command/Command.php`, `overrides/webklex/php-imap/src/{Message,Attachment,Query/Query,Connection/Protocols/ImapProtocol}.php`, plus `overrides/symfony/var-dumper/...`; wired via composer `autoload.files` / `include-path` style prepend (see `composer.json` autoload section at pin).
**Signature:** same FQCN as originals — e.g. `Swift_Transport_AbstractSmtpTransport.send` lives at `overrides/swiftmailer/.../AbstractSmtpTransport.php:183` per graph (`ext-freescout.overrides.swiftmailer...send`, rank#1 for "send reply swiftmailer").
**Data Shape:** full-file replacements, not subclasses; each carries upstream license header + inline `// FREESCOUT` change markers.

### Decisive source
```text
$ ls overrides/
swiftmailer  symfony  var-dumper? -> symfony  webklex
$ codebase-memory search_graph 'send reply swiftmailer' project=ext-freescout
-> overrides/swiftmailer/swiftmailer/lib/classes/Swift/Transport/AbstractSmtpTransport.php 183-232 (rank#1)
```
Concrete behavioral patches visible at pin: AbstractSmtpTransport keeps `\MailHelper::$smtp_data_sent`/registerPlugin hooks so SwiftGetSmtpQueueId can capture `queued as <id>` responses; MailTransport/SendmailTransport adjusted for FreeScout logging; webklex Message gains `fetchNewMail` (:1077) and charset-tolerant parsing used by tests/Fixtures/FixtureWebklexMessage.
**Flow:** composer dump-autoload prefers overrides because they are prepended to the classmap; upgrading a dependency means REAPPLYING its override diff, which is why pinned versions live in composer.lock and updates are manual (`freescout:update` command).
**Invariant:** an override file REPLACES the whole vendor class — partial copies silently drop upstream fixes, so every bump must re-diff ALL overridden files. The graph indexes overrides as first-class classes (packages table lists `webklex 472`, `swiftmailer 340` nodes), making them searchable like core code.
**Probe:** `ls overrides/` (lists 31 vendor-name dirs incl. swiftmailer, symfony, webklex, nwidart) and `grep -c "smtp_data_sent" overrides/swiftmailer/swiftmailer/lib/classes/Swift/Transport/AbstractSmtpTransport.php` (= ≥2; exact 2 — the FreeScout-added static flag).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "AbstractSmtpTransport send", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the shadow-override technique ONLY when subclassing is impossible (statics, final, constructor coupling) and keep a re-diff checklist per dependency bump; adapt by preferring decorators/events first; omit this pattern in greenfield projects — it exists here because FreeScout pins old Swift/webklex releases. Coverage caveat: parse_partial flags some override/vendor files; decisive lines above verified from source at pin ab277253.
