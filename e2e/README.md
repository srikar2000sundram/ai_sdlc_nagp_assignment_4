# e2e

Playwright end-to-end tests: the real app in a real browser.

```text
cd e2e
npm install
npx playwright install chromium
npm test              # headless
npm run test:headed   # watch the browser
```

Playwright starts the Python app itself (see `playwright.config.ts`, `webServer`) and stops it afterwards. If something is already running on port 5000 it is reused. The test creates its own invoice and deletes it afterwards, so it passes whatever data that server holds.

| File | Purpose |
| --- | --- |
| `tests/over-limit-rejection.spec.ts` | The required test: a Manager presses Approve on a 75,000.00 invoice the test creates, sees the exact refusal reason, and the invoice stays pending in the approvals list and the invoices table. The invoice is deleted afterwards |
| `pages/InvoicesPage.ts` | Page object for creating and submitting an invoice |
| `pages/LoginPage.ts` | Page object for the sign-in screen |
| `pages/ApprovalsPage.ts` | Page object for the Approvals and Invoices tabs |
| `playwright.config.ts` | Settings: one worker, Chromium, automatic server start |

## Conventions

- Use page objects and **role-based locators** (`getByRole`, `getByLabel`). Never CSS or XPath selectors.
- Tests must be repeatable. Create your own data and remove it afterwards, as the existing test does. A test that changes the seed invoices needs a reset endpoint (see deferred task T024 in `specs/001-invoice-approval-limits/tasks.md`).
