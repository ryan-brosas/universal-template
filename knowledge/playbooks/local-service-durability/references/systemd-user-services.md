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

## Local overrides in a drop-in

`~/.config/systemd/user/myservice.service.d/override.conf`

```ini
[Service]
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=10
ExecStartPre=            # clears an installer-added preflight
ExecStart=
ExecStart=/usr/bin/myservice --foreground
```

A drop-in survives the installer regenerating the main unit; re-run
`systemctl --user daemon-reload` after editing it.

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
