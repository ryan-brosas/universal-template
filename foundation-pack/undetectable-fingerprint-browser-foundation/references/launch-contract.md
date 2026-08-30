<!-- capsule-v2 -->
# Launch contract — how does automation attach to the spoofed Chromium with zero client code?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** How do Puppeteer/Playwright/CDP pipelines adopt per-session fingerprint spoofing without changing automation code?

## Quick Start launch surface (README.md)
**Path/Symbol:** `README.md`:99–116 (Quick Start), :64–68 (framework compatibility).
**Signature:** N/A — CLI startup-parameter contract, not a callable.
**Data Shape:** inputs: fingerprint JSON path (`--itbrowser=`), profile data dir, proxy URI, CDP port; output: a Chromium process whose JS surfaces already answer from the profile.

### Decisive source
```bash
# README.md:104-115 (verbatim)
./itbrowser_fingerprint.exe
chrome --itbrowser=myfingerprint.json
chrome.exe --user-data-dir=data1 --itbrowser="D:\Program Files\chrome\1.json" --proxy-server="socks5://someuser:password@host:port" --remote-debugging-port=9222
```
README.md:65: "Puppeteer: Works by pointing to custom Chromium binary"; :121 source build = "merge the code with chromium source code."

**Flow:** generator CLI emits one profile JSON → patched Chromium launched with `--itbrowser=<path>` → each profile gets its own `--user-data-dir` (storage isolation is per-profile, not per-cookie) → network identity enters at process level via `--proxy-server` → automation attaches over CDP on `--remote-debugging-port=9222` exactly as to stock Chrome.
**Invariant:** all spoofing lives inside the browser binary + its JSON input. The client stack stays stock: swap only `executablePath`; never inject page-side scripts for what the binary already answers.
**Probe:** no test runner exists at pin (data/docs repo) — deterministic probe instead: `grep -n "itbrowser" /mnt/hdd/utopia/inspo/undetectable-fingerprint-browser/README.md` pins flag spellings at lines 110/115 (executed pass 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", file_pattern: "README.md", limit: 10 });
```

## Verdict
Adopt the flag contract and the isolation/proxy/CDP layering for any patched-browser port; adapt the generator CLI name and profile-JSON schema to your product; omit assumptions about patch internals (binary-only at this pin). Coverage caveat: contract documented in README only; no executable verifies it.
