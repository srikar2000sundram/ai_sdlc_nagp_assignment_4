/**
 * End-to-end test: a Manager is refused on an over-limit invoice, sees why, and nothing changes.
 * This is the one end-to-end test the assignment asks for: a rejected over-limit approval through the real UI.
 *
 * The test creates its own 75,000.00 invoice (above a Manager's 50,000 limit, within a Director's 500,000), so it
 * passes whatever the server already holds, for example after someone approved the seed invoice by hand.
 * It deletes that invoice afterwards, so the server is left as it was.
 */
import { expect, test } from '@playwright/test';
import { ApprovalsPage } from '../pages/ApprovalsPage';
import { InvoicesPage } from '../pages/InvoicesPage';
import { LoginPage } from '../pages/LoginPage';

test('a manager is refused on an over-limit invoice, sees why, and the invoice does not change', async ({ page, request }) => {
  const login = new LoginPage(page);
  const invoices = new InvoicesPage(page);
  const approvals = new ApprovalsPage(page);
  let invoiceId = '';

  try {
    await login.open();
    await login.signInAs('demo.manager');

    // Arrange: an invoice of 75,000.00 waiting for approval.
    invoiceId = await invoices.createDraft(`E2E Over-Limit ${Date.now()}`, '75000');
    await invoices.submit(invoiceId);
    await approvals.open();
    await expect(approvals.pendingEntry(invoiceId)).toBeVisible();

    // Act: the Manager presses Approve.
    await approvals.approve(invoiceId);

    // The reason is shown to the user...
    await expect(approvals.decisionError()).toHaveText(
      'A Manager may approve invoices up to 50,000.00; this invoice is 75,000.00 and needs a Director.',
    );

    // ...the invoice is still waiting in the approvals list...
    await expect(approvals.pendingEntry(invoiceId)).toBeVisible();

    // ...and the invoices table agrees: still Pending Approval, nobody recorded as the decider.
    await approvals.openInvoicesTab();
    await expect(approvals.invoiceRow(invoiceId)).toContainText('Pending Approval');
    await expect(approvals.invoiceRow(invoiceId)).not.toContainText('Approved');
  } finally {
    // Clean up through the API as the Admin (the only role that may delete), so repeated runs leave no trace.
    if (invoiceId) {
      const loginResponse = await request.post('/api/auth/login', { data: { username: 'demo.admin', password: 'ChangeMe123!' } });
      const { token } = await loginResponse.json();
      await request.delete(`/api/invoices/${invoiceId}`, { headers: { Authorization: `Bearer ${token}` } });
    }
  }
});
