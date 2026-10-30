import { expect, type Page } from '@playwright/test';

/** Page object for creating and submitting an invoice on the Invoices tab. Found by role and label only. */
export class InvoicesPage {
  constructor(private readonly page: Page) {}

  /**
   * Create a draft invoice and return its id (read from the new table row).
   * @param customer A customer name; use a unique one so the row can be found.
   * @param amount The amount, for example '75000'.
   */
  async createDraft(customer: string, amount: string): Promise<string> {
    await this.page.getByLabel('Customer name').fill(customer);
    await this.page.getByLabel('Amount').fill(amount);
    await this.page.getByRole('button', { name: 'Create invoice' }).click();
    const row = this.page.getByRole('row').filter({ hasText: customer });
    await expect(row).toBeVisible();
    return (await row.getByRole('cell').first().innerText()).trim();
  }

  /** Submit a draft for approval (its accessible button name includes the invoice id). */
  async submit(invoiceId: string) {
    await this.page.getByRole('button', { name: `Submit invoice ${invoiceId} for approval` }).click();
    await expect(this.page.getByRole('row').filter({ hasText: invoiceId })).toContainText('Pending Approval');
  }
}
