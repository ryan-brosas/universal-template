<!-- capsule-v2 -->
# Packages and verify — do composer packages, semver, and MySQL strict mode meet October publish requirements?

**Source:** Publishing packages + Developer Guide §Environment. **Question:** Are plugins/themes publish-ready with correct composer metadata and dev environment strictness?

## Publish seam
**Path/Symbol:** `composer.json`, version tags, `.env`/MySQL config.
**Signature:** `acme/blog-plugin`; semver tags; STRICT_TRANS_TABLES.
**Data Shape:** `"name": "acme/blog-plugin", "type": "october-plugin"`.

### Decisive pattern
```json
{
  "name": "acme/blog-plugin",
  "type": "october-plugin",
  "require": {
    "composer/installers": "~1.0"
  }
}
```

**Flow:** **composer package name** MUST end with **`-plugin`** or **`-theme`** → set **`type`**: **`october-plugin`** / theme equivalent → include **`composer/installers`** dependency → **git repo** named **`{name}-plugin`** or **`oc-{name}-plugin`** (themes `-theme`) → **semver** tag releases — breaking changes require **major** bump per SemVer → declare **October CMS version** and cross-plugin deps in **`composer.json`** → development MySQL SHOULD enable **`STRICT_TRANS_TABLES`** (`sql_mode=STRICT_TRANS_TABLES`) to catch schema/type issues early → pre-publish verify: **PSR-1/2/4** + **October naming checklist** (vendor, tables, views, components) → increment plugin **`version.yaml`** / version file when tagging.
**Invariant:** composer name missing `-plugin`/`-theme`, absent semver discipline, or strict mode disabled in dev without documented reason fails publish/verify gate.
**Probe:** validate `composer.json` name/type; check git tags semver; confirm sql_mode in dev env docs.

## Verdict
October marketplace composer packaging, semver releases, and strict MySQL dev verification. Learning note: `october-style-learning-note.md`.
