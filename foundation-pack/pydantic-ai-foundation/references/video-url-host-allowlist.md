<!-- capsule-v2 -->
# VideoUrl YouTube host allowlist — why is a host list exact-match, and what breaks when you extend it?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should a "provider can resolve this URL" predicate be written so extension doesn't silently change other providers' behavior?

## video-url-host-allowlist
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py::VideoUrl.is_youtube` (:352–360).
**Signature:** property → `return urlparse(self.url).hostname in ('youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com')`.
**Data Shape:** exact-host tuple; `m.youtube.com` added by #7592; `music.youtube.com` DELIBERATELY excluded.

### Decisive source
```python
# Exact hosts, not a `.youtube.com` suffix match: Google rejects `music.youtube.com`
# as a `file_uri` with 400 INVALID_ARGUMENT, on the Gemini API and on Vertex alike,
# so a suffix match would hand it a URL it cannot resolve. Membership is also read by
# `download_item`, so a host added here stops being downloadable on every other
# provider too — verify both before extending this.
return urlparse(self.url).hostname in ('youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com')
```

**Flow:** user passes a media URL → `is_youtube` decides whether it rides Google's native file_uri channel vs generic download-and-upload → exact tuple match keeps non-resolvable YouTube-owned hosts on the universal download path.
**Invariant:** three rules:
1. Suffix matching is WRONG here even though every listed host IS youtube-owned: the predicate's meaning is "the provider resolves this directly", and Google 400s on music.youtube.com — ownership ≠ resolvability.
2. Dual-reader coupling: the same membership feeds BOTH the native-channel decision AND `download_item`'s skip logic, so extending the tuple silently changes behavior on EVERY OTHER provider too. The comment mandates verifying both before adding a host.
3. Hostname comparison via `urlparse(...).hostname` (lowercased, port-stripped) — comparing netloc strings would break on ports/case.
**Probe:** `tests/test_messages.py` (m.youtube.com cases) + `tests/models/test_google.py` (channel routing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "VideoUrl is_youtube hostname youtube download_item file_uri", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-host tuples + dual-reader documentation for any provider-capability predicate over URLs; adapt hosts/providers; never generalize the matcher without re-proving each host against the rejecting API.
