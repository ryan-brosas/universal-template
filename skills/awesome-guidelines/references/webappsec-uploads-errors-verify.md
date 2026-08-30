<!-- capsule-v2 -->
# Uploads, errors, and verify — are files safely stored and failures non-revealing with QA probes passing?

**Source:** WebAppSec §Uploads, §Error Handling, §Logging; Secure Coding QA Checklist. **Question:** Do uploads avoid executable content and do errors/logs protect system detail?

## Upload seam
**Path/Symbol:** file upload handlers, static file serving.
**Signature:** whitelist type; server filename; separate domain; image rewrite.
**Data Shape:** content-type from detection; block crossdomain.xml / .htaccess.

### Decisive pattern
```
store: /data/uploads/{uuid}.jpg   # never user-supplied basename
serve: https://files.example.com/{uuid}.jpg  Content-Type: image/jpeg
image pipeline: rewrite/strip metadata via library
```

**Flow:** **whitelist** extension and detected MIME → **max size** for file and archive members → **server-generated** storage names — never user text in paths → serve uploads from **separate domain** → **images**: rewrite/validate with image library; extension from detected type → **archives**: verify type, cap decompressed size → **block** `crossdomain.xml`, `clientaccesspolicy.xml`, `.htaccess`, `.htpasswd` → set **Content-Type** from detection not client header alone.
**Invariant:** user-controlled path/filename on disk, or app-origin upload served as HTML/JS, fails upload review.
**Probe:** upload `.php.jpg`, `.htaccess`, zip bomb sample in test env; verify Content-Type and domain.

## Error handling seam
**Flow:** user sees **generic** message — no stack/diagnostic/debug → **debug mode** stage only → logs: prevent **log forging** (newlines) and **XSS in web log viewers** (encode HTML) → pattern: log detail server-side; optional **error code** for support correlation.
**Invariant:** stack trace or SQL error in user response, or prod debug=true, fails error-handling review.
**Probe:** trigger 500/404 — response body; check DEBUG env in prod configs.

## Verify seam (QA checklist)
**Flow:** run Mozilla QA probes — **input** special chars in form/URL/hidden → graceful → **SQLi** parameterized → **output encoding** on user HTML → **CSRF** on mutations → **X-Frame-Options** on HTML → pair with dependency audit from `security-and-hardening`.
**Probe:**
```bash
# project-specific — map to infrasec-qa:* whiteboard codes
curl -X POST … # CSRF missing → rejected
curl -I …      # X-Frame-Options present
```

## Verdict
Safe upload pipeline, generic user errors, QA checklist green on changed surfaces. Learning note: `webappsec-style-learning-note.md`.
