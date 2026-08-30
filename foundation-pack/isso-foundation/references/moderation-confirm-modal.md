<!-- capsule-v2 -->
# Moderation confirm modal — how does a GET link perform a state-changing POST safely?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What does the GET branch of `/id/<id>/<action>/<key>` return, and how is the redirect target embedded?

## Confirm-then-POST modal
**Path/Symbol:** `isso/views/comments.py:API.moderate` (lines 812–842).
**Signature:** GET → HTML `<script>` page; POST → performs action.
**Data Shape:** `link = local("origin") + thread["uri"] + "#isso-%i" % item["id"]`; injected via `json.dumps(link)`.

### Decisive source
```python
if request.method == "GET":
    modal = (
        "<!DOCTYPE html>"
        "<html>"
        "<head>"
        "<script>"
        "  if (confirm('%s: Are you sure?')) {"
        "      xhr = new XMLHttpRequest;"
        "      xhr.open('POST', window.location.href);"
        "      xhr.send(null);"
        ...
        "</script>" % (action.capitalize(), json.dumps(link))
    )
    return Response(modal, 200, content_type="text/html")
```

**Flow:** emailed moderation links are GETs; the modal asks for confirmation and re-issues the SAME URL as POST (which executes activate/delete/edit) then navigates to the thread anchor. The URL string is JSON-encoded so quote characters in origin/URI can't break out of the JS string literal.
**Invariant:** State changes only ever execute on POST; the GET rendering is inert. Action strings are constrained by the route's `<any(edit,activate,delete):action>` converter before reaching this code.
**Probe:** `grep -cF 'action.capitalize()' isso/views/comments.py` (`1`); `grep -cF 'json.dumps(link)' isso/views/comments.py` (`1`).
**Test:** `isso/tests/test_comments.py:testModify` (POST path; GET modal untested — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "moderate confirm POST window.location", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt GET-renders-confirm/POST-executes for email-driven actions. Adapt UX. Keep JSON-encoding of any dynamic value interpolated into inline script.
