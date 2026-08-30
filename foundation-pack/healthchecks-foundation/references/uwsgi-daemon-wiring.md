<!-- capsule-v2 -->
# uwsgi daemon wiring — one container, three cooperating processes, healthcheck that reads settings without Django

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does the reference deployment run web + scheduler + reporter + optional SMTP in one box, and why is the container HEALTHCHECK a hand-rolled script instead of curl?

## docker/uwsgi.ini + Dockerfile + fetchstatus.py
**Path/Symbol:** `docker/uwsgi.ini` (hook-pre-app, attach-daemon trio, SMTPD_PORT conditional, harakiri=10); `docker/Dockerfile` (two-stage wheels, USER hc, HEALTHCHECK --start-period=20s CMD ./fetchstatus.py); `docker/fetchstatus.py:1-40` (SITE_ROOT resolution twin of settings.py).
**Signature:** ini directives: `hook-pre-app = exec:./manage.py migrate`; `attach-daemon = ./manage.py sendalerts --skip-checks`; `attach-daemon = ./manage.py sendreports --loop --skip-checks`; `if-env = SMTPD_PORT / attach-daemon = ./manage.py smtpd --port %(_)`.
**Data Shape:** Healthcheck cadence: start-period 20s, start-interval 5s, interval 60s, retries 1. fetchstatus hits `http://localhost:8000<SITE_ROOT-path>/api/v3/status/` with Host header = SITE_ROOT netloc; status endpoint executes SELECT 1.

### Decisive source
```python
# docker/fetchstatus.py — the comment explains the whole design
"""When making the HTTP request, we must pass a valid Host header and a valid
path (in case the app is not running at the root of the domnain). To
figure this out, we need to see `settings.SITE_ROOT`. Loading full
Django settings is a heavy operation so instead we replicate the logic that
settings.py uses for reading SITE_ROOT:

* Load it from `SITE_ROOT` environment variable
* if hc/local_settings.py exists, import it and read it from there"""

parsed_site_root = urlparse(SITE_ROOT.removesuffix("/"))
url = f"http://localhost:8000{parsed_site_root.path}/api/v3/status/"
headers = {"Host": parsed_site_root.netloc}
with urlopen(Request(url, headers=headers)) as response:
    assert response.status == 200
```

**Flow:** Container boot: migrate runs pre-app (idempotent gate) → uwsgi master binds :8000 (v4 or v6 via LISTEN_IPV6 if-env) → attach-daemon supervisors fork sendalerts, sendreports --loop, and conditionally smtpd; uwsgi restarts any that die. harakiri=10 kills stalled requests so a hung outbound webhook can't pin a worker. Dockerfile builds wheels with the C toolchain then installs into slim runtime as non-root `hc`, collectstatic+compress at build with build-time DEBUG=False SECRET_KEY.
**Invariant:** The daemons are SEPARATE PROCESSES precisely because sendalerts/sendreports install signal handlers and own DB connections — threads inside uwsgi workers would die with worker recycling and fight its process model. --skip-checks on daemons avoids triple-running system checks (the checks themselves live in hc/api/apps.py settings_check incl. the MariaDB UUID datatype detector E001). fetchstatus must NOT import django.settings: cold settings load defeats the 60s interval budget under memory pressure — it re-implements ONLY the SITE_ROOT resolution contract, and the Host header matters because ALLOWED_HOSTS validation runs before routing.
**Probe:** `hc/api/tests/test_status.py::test_it_works` (assertNumQueries(1), b"OK") — the endpoint fetchstatus probes; `hc/api/tests/test_system_checks.py::test_it_checks_apprise_and_private_ips` for the check suite wired by migrate.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "status healthcheck site root fetch", limit: 10 });
```

## Verdict
Adopt supervisor-per-daemon co-location with idempotent migrate gate, healthcheck endpoints that touch only the DB, and dependency-free probe scripts that duplicate config-resolution rather than import heavy frameworks. Adapt to systemd units/compose services/k8s sidecars — the contracts survive. Omit the v6 if-env branch freely; never omit non-root USER and build-time collectstatic pins.
