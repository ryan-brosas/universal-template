<!-- capsule-v2 -->
# Request-body content-type gate — Which requests are parsed as JSON, and what errors does a bad payload produce?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** When is a non-form body decoded as JSON vs passed through as bytes, and how are JSON syntax failures converted into 422s?

## Strict content-type parsing
**Path/Symbol:** `fastapi/routing.py:get_request_handler.app` (body block 426–473); `strict_content_type` plumbed from `APIRoute`/`_populate_api_route_state` (992) with `Default(True)` semantics.
**Signature:** inner closure of `get_request_handler(...)` → `app(request) -> Response`; gate inputs: `is_body_form` (body_field is `params.Form`), `content-type` header, `actual_strict_content_type`.
**Data Shape:** success ⇒ `body = parsed JSON value`; miss ⇒ `body = raw bytes` (validated later against the declared field, producing normal 422 loc errors).

### Decisive source
```python
                body_bytes = await request.body()
                if body_bytes:
                    json_body: Any = Undefined
                    content_type_value = request.headers.get("content-type")
                    if not content_type_value:
                        if not actual_strict_content_type:
                            json_body = await request.json()      # lenient mode only
                    else:
                        message = email.message.Message()
                        message["content-type"] = content_type_value
                        if message.get_content_maintype() == "application":
                            subtype = message.get_content_subtype()
                            if subtype == "json" or subtype.endswith("+json"):
                                json_body = await request.json()  # application/json AND *+json
                    if json_body != Undefined:
                        body = json_body
                    else:
                        body = body_bytes                       # NOT an error yet
        except json.JSONDecodeError as e:
            validation_error = RequestValidationError([{
                "type": "json_invalid", "loc": ("body", e.pos),
                "msg": "JSON decode error", "input": {},
                "ctx": {"error": e.msg}}], body=e.doc, endpoint_ctx=endpoint_ctx)
            raise validation_error from e
        except HTTPException:
            raise                                               # middleware-raised passes through
        except Exception as e:
            raise HTTPException(400, "There was an error parsing the body") from e
```

**Flow:** form bodies (`request.form()`) register `body.close` on the MIDDLEWARE exit stack so uploaded temp files outlive handler execution but close after send → JSON decode only for maintype `application` with subtype `json`/`*+json` → decode failure becomes a synthetic pydantic-style error entry whose loc points at the exact character offset (`e.pos`) → any other parse exception degrades to plain 400.
**Invariant:** (1) Wrong/absent content-type is NOT immediately fatal — bytes flow into field validation and surface as regular 422 validation errors; only syntactically broken JSON short-circuits with the `json_invalid` shape. (2) The `HTTPException` re-raise guard must wrap body reading because middlewares run inside this call chain; swallowing it would turn auth errors into 400 parse errors. (3) `strict_content_type=False` relaxes ONLY the missing-header case, not wrong types.
**Probe:** tests under `tests/test_enforce_content_type*` / docs_src-backed request-body suites exercise json_invalid offsets; the decisive excerpt above pins the subtype ladder byte-exactly.
