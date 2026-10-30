import { expect, type Page } from '@playwright/test';

/**
 * Page object for the sign-in screen.
 * Everything is found by role or label, never by CSS or XPath, so the tests read like what a user sees.
 */
export class LoginPage {
  constructor(private readonly page: Page) {}

  /** Open the app and wait for the Sign in heading. */
  async open() {
    await this.page.goto('/');
    await expect(this.page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    // Nobody is signed in yet, so there must be nothing to sign out of.
    await expect(this.page.getByRole('button', { name: 'Sign out' })).toBeHidden();
  }

  /**
   * Fill the form and sign in, then wait until the header shows who is signed in.
   * @param username One of the demo accounts, for example 'demo.manager'.
   * @param password Defaults to the shared demo password.
   */
  async signInAs(username: string, password = 'ChangeMe123!') {
    await this.page.getByLabel('Username').fill(username);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
    await expect(this.page.getByText(`${username} (`)).toBeVisible();
  }
}
