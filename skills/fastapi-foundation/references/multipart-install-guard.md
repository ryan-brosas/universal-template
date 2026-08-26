<!-- capsule-v2 -->
# Multipart install guard — Why does importing Form/File raise at route-definition time with two different messages?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How does FastAPI detect the wrong `multipart` package vs a missing one, and when is the check triggered?

## ensure_multipart_is_installed
**Path/Symbol:** `fastapi/dependencies/utils.py:ensure_multipart_is_installed` (103–129; message constants 88–100); invoked from `analyze_param` at 522–523 (`if isinstance(field_info, params.Form): ensure_multipart_is_installed()`).
**Signature:** `ensure_multipart_is_installed() -> None` (raises RuntimeError).
**Data Shape:** two failure modes: `ImportError` of both `python_multipart` and legacy `multipart` ⇒ "not installed" message; present-but-wrong `multipart` lacking `parse_options_header` ⇒ "incorrect install" message naming the uninstall/install commands.

### Decisive source
```python
    try:
        from python_multipart import __version__
        assert __version__ > "0.0.12"
    except (ImportError, AssertionError):
        try:
            from multipart import __version__
            assert __version__
            try:
                from multipart.multipart import parse_options_header
                assert parse_options_header
            except ImportError:
                logger.error(multipart_incorrect_install_error)
                raise RuntimeError(multipart_incorrect_install_error) from None
        except ImportError:
            logger.error(multipart_not_installed_error)
            raise RuntimeError(multipart_not_installed_error) from None
```

**Flow:** the check fires during PARAMETER ANALYSIS (`analyze_param`), i.e. at decorator/route-build time — an app with `Form()` params fails fast on import/registration rather than on first multipart request → version assert enforces python-multipart > 0.0.12 (the renamed canonical package).
**Invariant:** (1) Detection must be attribute-probing (`parse_options_header`) not name-based alone, because PyPI's `multipart` is an unrelated package that imports successfully. (2) Errors log AND raise — operators without logging still get the actionable message. (3) The guard belongs to form-field creation only; UploadFile-typed params route through the File inference path which also lands in Form handling.
**Probe:** `tests/test_no_swagger_ui_redirect.py`-style import tests aside, the pinned behavior lives in multipart-missing suites (`tests/test_multipart_installation*.py` if present at this pin) — decisive boundary: RuntimeError text matches one of the two constants above.
