#!/usr/bin/env python3
"""Sync the CLI-neutral MCP registry into Prime Agent's own settings.

Reads  ~/.agents/mcp/servers.json   (canonical, shared across CLIs)
Writes ~/.prime/agent/settings.json  (mcpServers block)  -- only with --apply

Translation rules (registry -> Prime Agent schema):
  * type "remote" -> "http"; "stdio" unchanged
  * drop "lifecycle" (Prime Agent has no such field)
  * env "${VAR}"  -> {"env": "VAR"}
  * env literal   -> NOT emittable (Prime Agent rejects literal stdio env);
                     reported so you can export it as a real env var.

Dry-run by default. Re-run with --apply to write. Merges (never clobbers
existing hand-added mcpServers entries).
"""
import json, os, re, sys, copy

AGENTS = os.path.expanduser("~/.agents/mcp/servers.json")
PRIME  = os.path.expanduser("~/.prime/agent/settings.json")
PLACEHOLDER = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def translate(name, s):
    out, problems = {}, []
    t = s.get("type", "stdio")
    out["type"] = "http" if t == "remote" else t
    for k in ("url", "command", "cwd"):
        if k in s:
            out[k] = s[k]
    if "args" in s:
        out["args"] = list(s["args"])
    env = s.get("env", {})
    if isinstance(env, dict) and env:
        newenv = {}
        for k, v in env.items():
            m = PLACEHOLDER.match(str(v))
            if m:
                newenv[k] = {"env": m.group(1)}
            elif os.environ.get(k) == str(v):
                newenv[k] = {"env": k}          # value matches an exported var of the same name
            else:
                problems.append(
                    f"{name}: env {k}={v!r} is a literal; Prime Agent needs an env-var "
                    f"reference. Add `export {k}={v}` to your shell profile, then it maps to {{\"env\": \"{k}\"}}."
                )
        if newenv:
            out["env"] = newenv
    return out, problems


def main():
    apply = "--apply" in sys.argv
    reg = json.load(open(AGENTS))["mcpServers"]
    servers, problems = {}, []
    for name, s in reg.items():
        t, p = translate(name, s)
        servers[name] = t
        problems += p

    prime = json.load(open(PRIME)) if os.path.exists(PRIME) else {}
    merged = copy.deepcopy(prime)
    merged.setdefault("mcpServers", {}).update(servers)

    print("=== resulting mcpServers ===")
    print(json.dumps(merged["mcpServers"], indent=2))
    print("\n=== issues to resolve before those servers connect ===")
    print("\n".join(problems) if problems else "(none)")
    if apply:
        with open(PRIME, "w") as f:
            json.dump(merged, f, indent=2)
            f.write("\n")
        print(f"\nWROTE {PRIME}\nRun `/reload` (or restart) then `await rlm.mcp.list_tools('<name>')`.")
    else:
        print("\n[dry-run] re-run with --apply to write.")


if __name__ == "__main__":
    main()
