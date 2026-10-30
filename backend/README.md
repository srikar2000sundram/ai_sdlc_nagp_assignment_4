# backend

The Python (FastAPI) service for the invoice approval app. It serves the JSON API and the static web UI.

## Layout

```text
backend/
  pyproject.toml          dependencies, pytest and mutmut settings
  src/invoice_app/
    domain/               business rules; no web or storage code
    api/                  routers, sign-in, serialization, in-memory repository, web UI (wwwroot/)
  tests/                  pytest tests (see tests/README.md)
```

## Run it

From the repository root:

```text
pip install -e "backend[dev]"
python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000
```

Open <http://localhost:5000>. Data lives in memory; restarting resets it.

## Test it

```text
python -m pytest backend/tests -q
```

## How the code is organised

- **`domain/`** holds the rules. `approval_policy.py` has one small class per approval rule and an `ApprovalPolicy` that asks them in order. `approval_service.py` is the workflow (submit, approve, reject). `repository.py` defines small storage contracts.
- **`api/`** translates HTTP to domain calls. `main.py` is the only place that chooses concrete classes (`create_app`). `error_handling.py` turns domain errors into status codes. `auth/` handles sign-in and sessions.
- Dependencies point one way: `api` imports `domain`, never the reverse.

The design follows the SOLID principles; see `docs/guides/19-solid-design.md`. Every module, class and function has a docstring, collected in `docs/guides/20-code-reference.md`.

## Rules in one table

| Invoice amount | Who may approve | Approvals needed |
| --- | --- | --- |
| up to and including 50,000.00 | Manager or Director | 1 |
| above 50,000.00, up to and including 500,000.00 | Director | 1 |
| above 500,000.00 | first: Manager or Director; second: Director | 2 different users |

A refused approval returns HTTP 403 with a reason and changes nothing.
