<!-- capsule-v2 -->
# One-click template contract: compose YAML ↔ base64 registry twin with env-var dialect split

## Source
Coolify `main@98116397`: `templates/compose/vault.yaml` (25L) + `templates/compose/obsidian-livesync.yaml` (60L), registry `templates/service-templates.json` + `service-templates-latest.json` (17-line entries each). Drift-introduced planes (upstream commits `dbc0aa52`, `5d06c226`); direct tests `tests/Unit/VaultServiceTemplateTest.php` (38L), `tests/Unit/ObsidianLiveSyncServiceTemplateTest.php` (24L).

## Question
What makes a Coolify one-click service template valid — and why does the same template exist in TWO dialects between the registry JSONs?

## Path / Symbol
Template header grammar (comment directives `# documentation/slogan/category/tags/logo/port`); `SERVICE_FQDN_*_<port>` vs `SERVICE_URL_*_<port>` env vars; bind-mount-with-inline-content (`type: bind, content: |`).

## Signature
```yaml
# vault.yaml (URL dialect)
environment:
  - SERVICE_URL_VAULT_8200            # plain URL var (no domain attached)
  - VAULT_API_ADDR=${SERVICE_URL_VAULT_8200}
# obsidian-livesync.yaml (FQDN dialect)
  - SERVICE_FQDN_COUCHDB_5984         # Coolify proxies port 5984 at assigned domain
  - COUCHDB_USER=${SERVICE_USER_COUCHDB}          # auto-generated, persisted under Env Vars
  - COUCHDB_PASSWORD=${SERVICE_PASSWORD_64_COUCHDB}  # 64-char generated secret
```
Registry entry: `{documentation, slogan, compose(base64), tags[], category, logo, minversion, template_last_updated_at, port}`.

## Data Shape
The registries embed the SAME compose base64-encoded; tests `base64_decode(..., strict: true)` and assert against decoded content — the yaml file and its embedded twin must never diverge.

## Decisive source
VaultServiceTemplateTest pins the DIALECT SPLIT explicitly:
```php
expect($generatedCompose)->toContain($templateFile === 'service-templates.json'
    ? 'VAULT_API_ADDR=${SERVICE_FQDN_VAULT_8200}'     // stable catalog rewrote to FQDN form
    : 'VAULT_API_ADDR=${SERVICE_URL_VAULT_8200}');    // latest keeps the authored URL form
```
i.e. the two registries intentionally serve different generations of the template; a sync tool that naively copies one over the other fails the test.

## Flow / Invariant
INVARIANTS:
1. Header comments ARE machine-read metadata (port/category drive UI + registry fields).
2. `SERVICE_FQDN_<name>_<port>` = "attach my domain+proxy"; `SERVICE_URL_*` = plain URL injection — choosing wrong breaks TLS-fronted services.
3. Generated credentials use `SERVICE_PASSWORD[_64]_...` placeholders — never literal secrets or plain `${VAR}` defaults in templates.
4. Inline bind-mount `content:` blocks let a template ship config files (CouchDB local.ini with CORS origins pinned to Obsidian app origins) without extra scripts.
5. Registry `compose` field must decode byte-faithfully to the working yaml (strict base64 + toContain pins); `template_last_updated_at: null` is legal for new entries.

## Probe (direct tests)
From repo root:
```bash
grep -c 'SERVICE_FQDN_COUCHDB_5984' templates/compose/obsidian-livesync.yaml
grep -c 'VAULT_API_ADDR=${SERVICE_URL_VAULT_8200}' templates/compose/vault.yaml
python3 -c "import json,base64;d=json.load(open('templates/service-templates.json'));print(len(base64.b64decode(d['vault']['compose'],validate=True)))"
grep -c "service-templates.json'" tests/Unit/VaultServiceTemplateTest.php
```
Expect 1 / 1 / >0 (decodable bytes) / ≥1. (PHPUnit runner blocked honestly; JSON/base64 side executed via stdlib.)

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"obsidian livesync couchdb service template","limit":3}'
```
→ hits in `resources/views/components/service/configuration-sidebar.blade.php` family + template-adjacent Section nodes; template YAML itself is data (not parsed into function nodes) — cite file paths directly when porting.

## Verdict
ADAPT — the directive-header + twin-registry + placeholder-credential contract ports to any app-catalog system; the specific services are examples.
