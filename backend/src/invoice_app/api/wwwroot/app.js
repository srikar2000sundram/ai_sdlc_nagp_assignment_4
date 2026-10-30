/**
 * Invoice Approvals web UI (plain JavaScript, no build step).
 *
 * Signs a user in, lists invoices, and lets approvers approve or reject pending ones. All business rules live on
 * the server: this file only shows what the API returns, including the reason when an approval is refused.
 *
 * Everything is wrapped in a function so nothing leaks into the global scope.
 */
(() => {
  // Display formatting only. The server keeps exact decimals; the UI just shows them as dollars.
  const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
  // Shorthand: find an element by id.
  const $ = (id) => document.getElementById(id);
  // The signed-in user ({ token, username, role }). Kept in sessionStorage so a page refresh does not sign out.
  let session = JSON.parse(sessionStorage.getItem('session') || 'null');

  /**
   * Build a DOM element. Using this instead of innerHTML means server text is never parsed as HTML.
   * @param {string} tag Element name, for example 'button'.
   * @param {Object} attrs Attributes; the key 'class' sets the class name.
   * @param {...(Node|string)} children Child nodes or text.
   */
  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === 'class') node.className = value;
      else node.setAttribute(key, value);
    }
    for (const child of children) node.append(child);
    return node;
  }

  /**
   * Call the JSON API with the signed-in user's bearer token.
   * A 401 means the session is gone, so sign out. Any other failure throws an Error carrying the
   * server's own message (the `error` field), so callers can show a clear reason to the user.
   * @param {string} path Path under /api, for example '/invoices'.
   * @param {RequestInit} options Fetch options.
   * @returns {Promise<any>} The parsed JSON body, or null for 204.
   */
  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (session) headers.Authorization = `Bearer ${session.token}`;
    const response = await fetch(`/api${path}`, { ...options, headers });
    if (response.status === 401 && session) { signOut(); throw new Error('Session expired.'); }
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) throw new Error((body && body.error) || `Request failed (${response.status})`);
    return body;
  }

  /** Show or hide an element by id. */
  function show(id, visible) { $(id).hidden = !visible; }
  /** Put a message in an alert paragraph (role=alert) and reveal it; an empty message hides it. */
  function showError(id, message) { const p = $(id); p.textContent = message || ''; p.hidden = !message; }

  /** Switch between the sign-in view and the app view depending on whether someone is signed in. */
  function render() {
    const signedIn = !!session;
    show('login-view', !signedIn);
    show('app-view', signedIn);
    show('session-bar', signedIn);
    if (signedIn) {
      $('whoami').textContent = `${session.username} (${session.role})`;
      refresh();
    }
  }

  /** Reload invoices from the server and redraw both the invoices table and the pending approvals list. */
  async function refresh() {
    const invoices = await api('/invoices');
    renderInvoices(invoices);
    renderPending(invoices.filter((i) => i.status === 'PendingApproval'));
  }

  /**
   * The Status cell: a coloured pill, and for a rejected invoice the reason and who rejected it,
   * so everyone who can see the invoice can see why it was turned down.
   */
  function statusCell(invoice) {
    const pill = el('span', { class: `status status-${invoice.status}` }, invoice.status.replace(/([a-z])([A-Z])/g, '$1 $2'));
    if (invoice.status !== 'Rejected') return [pill];
    const reason = invoice.decisionNote || 'No reason recorded';
    const who = invoice.decidedBy ? ` (rejected by ${invoice.decidedBy})` : '';
    return [pill, el('div', { class: 'decision-note' }, `Reason: ${reason}${who}`)];
  }

  /** Draw the invoices table. Draft invoices get a Submit button; the status text is split into words (PendingApproval to Pending Approval). */
  function renderInvoices(invoices) {
    const body = $('invoices-table').querySelector('tbody');
    body.replaceChildren(...invoices.map((invoice) => {
      const actions = el('td');
      if (invoice.status === 'Draft') {
        const submit = el('button', { type: 'button', class: 'secondary', 'aria-label': `Submit invoice ${invoice.id} for approval` }, 'Submit for approval');
        submit.addEventListener('click', async () => { await api(`/invoices/${invoice.id}/submit`, { method: 'POST' }); refresh(); });
        actions.append(submit);
      }
      return el('tr', {},
        el('td', {}, invoice.id),
        el('td', {}, invoice.customerName),
        el('td', {}, money.format(invoice.amount)),
        el('td', {}, ...statusCell(invoice)),
        actions);
    }));
  }

  /**
   * Draw the pending approvals list: an Approve button and a reason box with a Reject button for each invoice.
   * Invoices that need more than one approval show progress such as '1 of 2 approvals'.
   */
  function renderPending(pending) {
    show('pending-empty', pending.length === 0);
    $('pending-list').replaceChildren(...pending.map((invoice) => {
      const reasonId = `reason-${invoice.id}`;
      const approve = el('button', { type: 'button', 'aria-label': `Approve invoice ${invoice.id}` }, 'Approve');
      const reject = el('button', { type: 'button', class: 'danger', 'aria-label': `Reject invoice ${invoice.id}` }, 'Reject');
      const reason = el('input', { id: reasonId, 'aria-label': `Rejection reason for ${invoice.id}`, placeholder: 'Reason (required to reject)' });

      approve.addEventListener('click', () => decide(`/approvals/${invoice.id}/approve`, {}));
      reject.addEventListener('click', () => decide(`/approvals/${invoice.id}/reject`, { reason: reason.value }));

      // Only invoices above the Director limit need two approvals, so progress is shown just for them.
      const details = [
        el('span', { class: 'inv-id' }, invoice.id),
        el('span', { class: 'inv-customer' }, invoice.customerName),
        el('span', { class: 'inv-amount' }, money.format(invoice.amount)),
      ];
      if (invoice.requiredApprovals > 1) {
        details.push(el('span', { class: 'progress' }, `${invoice.approvals.length} of ${invoice.requiredApprovals} approvals`));
      }

      return el('li', {},
        el('div', { class: 'info' }, ...details),
        el('span', {}, approve),
        el('div', { class: 'reject-row' }, reason, reject));
    }));
  }

  /**
   * Send an approve or reject request, then reload. If the rules refuse it (HTTP 403) the server's reason is shown
   * under the list and nothing else changes, because the server leaves the invoice untouched.
   */
  async function decide(path, payload) {
    showError('decision-error', '');
    try {
      await api(path, { method: 'POST', body: JSON.stringify(payload) });
      await refresh();
    } catch (error) {
      showError('decision-error', error.message);
    }
  }

  /** Forget the session locally, tell the server to forget the token (best effort), and show the sign-in view. */
  function signOut() {
    if (session) api('/auth/logout', { method: 'POST' }).catch(() => {});
    session = null;
    sessionStorage.removeItem('session');
    // Messages belong to the person who triggered them: do not show them to the next user.
    for (const id of ['decision-error', 'create-error', 'login-error']) showError(id, '');
    // First draw when the page loads.
    render();
  }

  // Sign in: exchange username and password for a token, remember it, and show the app.
  $('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    showError('login-error', '');
    try {
      const result = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: $('username').value, password: $('password').value })
      });
      session = { token: result.token, username: result.username, role: result.role };
      sessionStorage.setItem('session', JSON.stringify(session));
      $('password').value = '';
      showError('decision-error', '');
      render();
    } catch (error) {
      showError('login-error', error.message);
    }
  });

  // Create a draft invoice. The server validates the amount and customer name and answers with a readable message.
  $('new-invoice-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    showError('create-error', '');
    try {
      await api('/invoices', {
        method: 'POST',
        body: JSON.stringify({ customerName: $('customer').value, amount: Number($('amount').value) })
      });
      $('new-invoice-form').reset();
      refresh();
    } catch (error) {
      showError('create-error', error.message);
    }
  });

  // The Sign out button.
  $('sign-out').addEventListener('click', signOut);

  // Tabs: select one, hide the other panel (aria-selected keeps the tabs accessible and testable by role).
  for (const tab of ['invoices', 'approvals']) {
    $(`tab-${tab}`).addEventListener('click', () => {
      for (const other of ['invoices', 'approvals']) {
        $(`tab-${other}`).setAttribute('aria-selected', String(other === tab));
        show(`${other}-panel`, other === tab);
      }
    });
  }

  render();
})();
