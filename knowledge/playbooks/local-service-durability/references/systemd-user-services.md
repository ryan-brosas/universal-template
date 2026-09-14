# systemd --user service recipes

Checked against systemd on a current Linux host. Verify wording with
`systemctl --help` when behavior matters.

## Inspect effective configuration

```sh
systemctl --user show myservice.service \
  -p ExecStart -p ExecStartPre -p Restart -p RestartSec -p KillMode -p NRestarts -p MainPID
systemctl --user cat myservice.service        # generated unit + drop-ins, in load order
systemctl --user list-dependencies myservice.service | head
```

Properties are printed in systemd's own order, not the order requested, and an
empty property prints as a blank line, so match on the `Key=` prefix when
parsing instead of counting lines.

## Update the tree the unit actually runs

One host commonly holds several runtime installs (`mise`, a bundled IDE runtime,
`nvm`), each with its own global package tree. The caller's `PATH` decides which
tree `npm install -g` and a tool's self-updater touch, and it is often not the
tree named in `ExecStart`.

`ExecStart` is a list property: `-p ExecStart --value` prints
`{ path=... ; argv[]=... ; ; }`, so taking the first space-separated token yields
`{` and a bogus `PATH`. Its `path=` can also name a wrapper such as `/usr/bin/env`,
not the interpreter. For a running Node service, resolve the supervised process
before stopping it and retain `ExecStart` only as audit evidence:

```sh
unit=myservice.service
ExecStart=$(systemctl --user show "$unit" -p ExecStart --value)
main_pid=$(systemctl --user show "$unit" -p MainPID --value)
[ "${main_pid:-0}" -gt 0 ] || { echo "unit is not running" >&2; exit 1; }
node_bin=$(readlink -f "/proc/$main_pid/exe")
case "$(basename "$node_bin")" in node|nodejs) ;;
  *) echo "service process is not Node: $node_bin" >&2; exit 1 ;;
esac
node_dir=$(dirname "$node_bin")
npm_bin="$node_dir/npm"                     # the runtime's own npm, not PATH's
[ -x "$npm_bin" ] || { echo "no npm beside $node_bin" >&2; exit 1; }
# The unit's environment lacks your shell's npm variables, and an ambient
# npm_config_prefix overrides derivation outright: on one host the same two
# npm binaries reported /usr and the IDE runtime until these were cleared.
npm_env=(env -u npm_config_prefix -u npm_config_global_prefix \
  -u npm_config_userconfig -u npm_config_globalconfig)
prefix=$("${npm_env[@]}" PATH="$node_dir:$PATH" "$npm_bin" prefix -g)
echo "effective:   $ExecStart"
echo "unit runs:   $node_bin"
echo "npm:         $npm_bin"
echo "target tree: $prefix"
```

`argv[]=` in the same string carries the entry script when that path is needed.
For a stopped unit, fully resolve wrapper arguments and the script interpreter
before selecting a package tree. `/proc/<MainPID>/cmdline` may be rewritten by the
daemon's process title, so it is not a reliable source.

The CLI that ran the updater and the tree `ExecStart` names often disagree, and
the updater's version check reads its own tree, so it can report *already on the
latest version* while the service-owned tree stays old. On a real host the
interactive `command -v` and `npm root -g` resolved to a JetBrains-bundled
runtime while the unit ran a `mise` install; the updater upgraded the bundled
copy and left the unit's tree untouched. Replacing the service-owned tree
directly:

```sh
(
  systemctl --user stop "$unit" || exit $?
  install_status=0
  "${npm_env[@]}" PATH="$node_dir:$PATH" "$npm_bin" install -g pkg@<version> || install_status=$?
  start_status=0
  systemctl --user start "$unit" || start_status=$?
  [ "$install_status" -eq 0 ] || exit "$install_status"
  exit "$start_status"
)
```

Confirm the update landed at the service-owned tree, then probe the service:

```sh
"$node_bin" -p "require('$prefix/lib/node_modules/<scope>/<pkg>/package.json').version"
systemctl --user show "$unit" -p MainPID -p ExecStart --value   # new pid, unchanged command
curl -fsS --max-time 5 http://127.0.0.1:<port>/health          # readiness, when exposed
<one representative request the service exists to serve>        # the operation itself
pgrep -af '<entry-script>'                                      # exactly one process
ss -ltnp | grep <port>                                          # one listener, that pid
command -v pkgdir-or-cli                                        # may still name the other tree
```

## Local overrides in a drop-in

`~/.config/systemd/user/myservice.service.d/override.conf`

```ini
[Unit]
StartLimitIntervalSec=60
StartLimitBurst=10

[Service]
Restart=always
RestartSec=5
# Clear an installer-added preflight, then replace the inherited command.
ExecStartPre=
ExecStart=
ExecStart=/usr/bin/myservice --foreground
```

A drop-in survives the installer regenerating the main unit; re-run
`systemctl --user daemon-reload` after editing it. Run
`systemd-analyze verify <unit>` on a unit or drop-in before installing it:
unit files have no inline comments, so `Key= # text` becomes a command, and
`StartLimitIntervalSec` / `StartLimitBurst` are ignored outside `[Unit]`.
Verify reports both, as it did on the example above before this note was added.

## Classify the unit before deciding

`systemctl is-active` exits nonzero for both `inactive` and `failed`, so the
printed state, never the exit status, picks the branch. Verified on a real host:
a `start-limit-hit` unit printed `failed` with `Result=start-limit-hit`, a
deliberately stopped unit printed `inactive`, and both exited 3.

```sh
state=$(systemctl --user is-active myservice.service)
case "$state" in
  active)  probe the service ;;                                    # then recover on probe failure
  failed)  reset-failed; restart ;;                                # systemd is NOT retrying a failed unit
  activating|deactivating|inactive) : ;;                           # already retrying, or a human stopped it
esac
```

`try-restart` is a no-op on any unit that is not running, so a recovery path
built on it silently does nothing exactly when the unit is down. Treat
`failed` as conclusive (recover on first observation, still paced) and leave
`inactive` alone so deliberate stops are respected.

## Crash-loop-safe healthcheck

```sh
systemctl --user reset-failed myservice.service 2>/dev/null || true
systemctl --user restart myservice.service
systemctl --user is-active --quiet myservice.service
```

Evidence for the `reset-failed` step, reproduced twice on a real deployment: a
unit driven into `start-limit-hit` answered a plain `restart` with
*"start of the service was attempted too often"* and stayed down; after
`reset-failed` the same `restart` succeeded. A health script that only calls
`try-restart` strands such a unit permanently.

Bound the probe itself (`curl -fsS --max-time N`) and treat the exit status as
the only signal; a probe that hangs inside a oneshot unit becomes the outage.

## Reboot durability

```sh
systemctl --user is-enabled myservice.service   # expected: enabled
loginctl show-user "$USER" -p Linger            # expected: Linger=yes
```

## Fault injection

```sh
before=$(systemctl --user show myservice.service -p MainPID --value)
kill -9 "$before"
for i in $(seq 1 15); do sleep 1
  after=$(systemctl --user show myservice.service -p MainPID --value)
  [ "$after" != "$before" ] && [ "$after" != 0 ] && break
done
echo "recovered in ${i}s with pid $after"
systemctl --user stop myservice.service
systemctl --user start myservice-healthcheck.service
systemctl --user is-active myservice.service        # must be active again
```

## Exposure review after an installer run

```sh
tailscale serve status    # reverse-proxy / tailnet mappings
tailscale funnel status   # public mappings
ss -ltnp | grep <port>
```

Revert a mapping the installer created but nobody asked for, for example
`tailscale serve --https=443 off`, then re-check that status reports
`No serve config`.
