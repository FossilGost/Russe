/* Revalidate private pages after history navigation or an account switch. */
(() => {
  const account = document.body.dataset.userId || '';
  const key = 'slovo:active-account';
  const hide = () => { document.body.hidden = true; };
  const reload = () => { hide(); window.location.reload(); };
  try { localStorage.setItem(key, account); } catch (_) { /* Server checks remain authoritative. */ }
  window.addEventListener('storage', event => {
    if (event.key === key && event.newValue !== account) reload();
  });
  window.addEventListener('pagehide', () => { if (account) hide(); });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { reload(); return; }
    document.body.hidden = false;
  });
})();
