# Quickstart / Validation

```bash
pip install -e "backend[dev]"
python -m pytest backend/tests -q                       # unit + API tests
python -m uvicorn invoice_app.api.main:app --app-dir backend/src --port 5000
cd e2e && npm install && npx playwright install chromium && npm test
wsl bash scripts/run_mutation.sh after                  # mutation report -> docs/mutation/after.txt
```

Manual check (UI at http://localhost:5000):

1. Sign in as `demo.manager` / `ChangeMe123!`, Approvals tab, Approve `INV-2001` (75,000.00) → alert with the Manager-limit reason; invoice stays pending.
2. Sign in as `demo.director`, Approve `INV-2001` → Approved.
3. As `demo.director`, Approve `INV-2002` (600,000.00) → still pending, "1 of 2 approvals". Approve again → refused (already approved). Sign in as `demo.director2`, approve → Approved.
