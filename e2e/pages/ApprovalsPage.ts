import { expect, type Locator, type Page } from '@playwright/test';

/** Page object for the Approvals and Invoices tabs. Found by role and accessible name only. */
export class ApprovalsPage {
  constructor(private readonly page: Page) {}

  /** Switch to the Approvals tab and wait for its heading. */
  async open() {
    await this.page.getByRole('tab', { name: 'Approvals' }).click();
    await expect(this.page.getByRole('heading', { name: 'Pending approvals' })).toBeVisible();
  }

  /** The list item for one pending invoice. */
  pendingEntry(invoiceId: string): Locator {
    return this.page.getByRole('listitem').filter({ hasText: invoiceId });
  }

  /** Press the Approve button of one invoice (its accessible name includes the invoice id). */
  async approve(invoiceId: string) {
    await this.page.getByRole('button', { name: `Approve invoice ${invoiceId}` }).click();
  }

  /** The alert that shows why an approval was refused. */
  decisionError(): Locator {
    return this.page.getByRole('alert').filter({ hasText: /\S/ });
  }

  /** Switch to the Invoices tab. */
  async openInvoicesTab() {
    await this.page.getByRole('tab', { name: 'Invoices' }).click();
  }

  /** The table row for one invoice. */
  invoiceRow(invoiceId: string): Locator {
    return this.page.getByRole('row').filter({ hasText: invoiceId });
  }
}
