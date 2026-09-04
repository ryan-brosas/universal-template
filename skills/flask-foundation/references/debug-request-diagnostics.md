<!-- capsule-v2 -->
# Debug-only request diagnostics — what do the enctype and FormDataRoutingRedirect helpers catch, and via what mechanism?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How are these developer-error traps attached and when do they deliberately NOT fire?

## attach_enctype_error_multidict + raise_routing_exception
**Path/Symbol:** `src/flask/debughelpers.py:attach_enctype_error_multidict` (81–104), `.FormDataRoutingRedirect` (50–78), `.DebugFilesKeyError` (23–47); triggers at `src/flask/wrappers.py:Request._load_form_data` (197–210) and `src/flask/app.py:Flask.raise_routing_exception` (563–589).
**Signature:** patch = swap `request.files.__class__` to an ad-hoc subclass overriding `__getitem__`.
**Data Shape:** trap fires only when `current_app.debug AND mimetype != "multipart/form-data" AND not self.files`.

### Decisive source
```python
oldcls = request.files.__class__
class newcls(oldcls):
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError as e:
            if key not in request.form:
                raise                          # genuinely unknown key → normal error
            raise DebugFilesKeyError(request, key).with_traceback(e.__traceback__) from None
newcls.__name__ = oldcls.__name__
request.files.__class__ = newcls             # class swap, no wrapper object

# routing redirect trap:
if (not self.debug
    or not isinstance(request.routing_exception, RequestRedirect)
    or request.routing_exception.code in {307, 308}
    or request.method in {"GET", "HEAD", "OPTIONS"}):
    raise request.routing_exception          # normal behavior
raise FormDataRoutingRedirect(request)       # debug + body-dropping redirect
```

**Flow:** form-data load attaches files-key trap (debug only); dispatch start re-checks a parked routing exception — a slash-redirect that would drop POSTed form data becomes an AssertionError naming the canonical URL.
**Invariant:** both traps convert silent data loss into loud AssertionErrors ONLY under debug; 307/308 preserve method+body so they stay exempt; the KeyError passthrough keeps unrelated missing-file errors honest.
**Probe:** `grep -Fc 'attach_enctype_error_multidict(self)' src/flask/wrappers.py` = 1; test `tests/test_basic.py::test_routing_redirect_debugging` (:1722) pins 301-vs-default redirect behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "routing exception RequestRedirect debug form data", limit: 6 });
```

## Verdict
Adopt the class-swap trap pattern and the redirect exemption set. Adapt exception types to AssertionError-equivalents. Omit explain_template_loading_attempts here (covered by loader capsule).
