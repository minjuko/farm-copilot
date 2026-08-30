# Backend dependency security audit

The virtual environment was checked with `pip-audit` 2.10.1 on 2026-08-30.
The application tests still pass, but the audit database reports 105 known
issues across 8 installed packages. This is an inventory for the portfolio
environment; it is not a claim that the current dependency set is suitable for
internet-facing production.

Direct runtime packages requiring an upgrade review:

| Package | Current pin | First reported fixed version (or newer) |
|---|---:|---:|
| Django | 5.0.6 | 5.2.17 / 6.0.8 |
| cryptography | 42.0.8 | 46.0.6 |
| Pillow | 10.3.0 | 12.2.0 |
| python-dotenv | 1.0.1 | 1.2.2 |
| requests | 2.32.3 | 2.32.4 |
| torch (optional YOLO runtime) | 2.3.1 | review 2.9+ compatibility with the model first |

The remaining findings are transitive packages pulled by the development
toolchain or optional AI runtime. `pip check` reports no broken requirements.
Do not run a blanket `pip install --upgrade` or `pip-audit --fix`: upgrades to
Django, Pillow, and Torch can change runtime behavior, and Torch is a large
optional install. Upgrade one package group at a time, run the full backend
test suite, and re-run the real model smoke test before accepting a change.

To reproduce the audit in a fresh virtual environment:

``` powershell
python -m pip install -r requirements.txt
python -m pip install pip-audit==2.10.1
python -m pip_audit --format=columns
```

For this portfolio repository, actual deployment is out of scope. Before any
public deployment, resolve all direct runtime findings and re-audit the final
lock/pip environment.
