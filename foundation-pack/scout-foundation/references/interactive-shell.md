<!-- capsule-v2 -->
# Interactive shell — how does a zero-framework menu loop stay responsive on Windows and never die mid-flow?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What are the boot-order rules (UTF-8 shim, argv filter, .env absorb) and the loop's error containment that keep a rich TUI alive?

## Console-first boot ladder + lazy platform imports + catch-all loop
**Path/Symbol:** `scout.py:win32 shim` (:10-13), `_args` filter (:19-42), `main` (:1060-1139), per-action lazy imports (:575, :586, :630, :641, :668, :679, :727).
**Signature:** `main() -> None`; dispatch via literal if/elif over `Prompt.ask(choices=[...])`.
**Data Shape:** only instagram+stealth import eagerly (:64-65); the other seven scrapers and httpx import inside their action functions.

### Decisive source
```python
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')            # code page → UTF-8 BEFORE rich prints
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_args = [a for a in sys.argv[1:] if a not in ('--verbose', '-V')]   # flag stripped
...
while True:
    ...
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Exiting...[/yellow]")
        break
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")   # menu NEVER dies; loop continues

# every action ends the same way:
_pause()
console.clear()
show_header()
```

**Flow:** boot order is load-bearing: (1) win32 code-page + stdout reconfigure so box-drawing/gradient glyphs don't crash CPython's cp1252 stdout, (2) argv filtering so `-V` reaches neither version/help matching nor scraper args, (3) `.env` absorb (env-persistence.md), (4) eager imports only for what the splash needs, (5) update-check thread (forced-update-gate.md). The REPL wraps every action in try/except Exception → print → `_pause` → clear → re-render header, so a crash inside one platform returns to the menu with state intact (`_session_stats` module-global survives).
**Invariant:** the UTF-8 shim must precede ANY console output — reconfiguring after rich has measured the stream leaves mojibake. KeyboardInterrupt exits the whole app (Ctrl-C = quit) but plain Exception never propagates out of the loop; conversely inside `_standard_scrape_loop`, Ctrl-C during an item aborts upward to this handler — the two layers intentionally disagree about who handles interrupts. Lazy per-platform imports keep cold-start instant and isolate requests/httpx import failures to the feature that needs them.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "chcp\|from app.scrapers" scout.py | head -12` pins the boot order (:10-13 vs :64-65 vs :575+); graph retrieval resolves `Scout.scout.main`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "main show_menu prompt choices", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered boot ladder (encoding → argv → env → imports → UI), lazy heavy imports behind menu actions, and exception-contained REPL loops for any interactive CLI; adapt branding/menus freely; omit the gradient ASCII art unless porting the product itself.
