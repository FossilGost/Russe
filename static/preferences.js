/* Apply immediately; serialize partial saves and keep unsynced changes locally. */
(() => {
  const endpoint = document.body.dataset.interfaceUrl;
  if (!endpoint) return;
  const account = document.body.dataset.userId;
  const storageKey = `slovo:${account}:pending-preferences`;
  const form = document.getElementById('settings-form');
  const status = document.getElementById('settings-save-status');
  const retry = document.getElementById('settings-retry');
  const fields = new Set(['name', 'goal', 'length', 'strict', 'sound', 'theme', 'voice', 'speech_rate', 'browser_voice', 'volume', 'keyboard_open']);
  let pending = {}, timer, saving = false;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    for (const [key, value] of Object.entries(saved)) {
      if (fields.has(key) && ['string', 'number'].includes(typeof value)) pending[key] = value;
    }
  } catch (_) { /* Saving still works without local storage. */ }
  const remember = () => {
    try {
      if (Object.keys(pending).length) localStorage.setItem(storageKey, JSON.stringify(pending));
      else localStorage.removeItem(storageKey);
    } catch (_) { /* Optional recovery on the next visit. */ }
  };
  function notify(message, state) {
    if (status) { status.textContent = message; status.dataset.state = state; }
    if (retry) retry.hidden = state !== 'error';
    let warning = document.getElementById('preferences-sync-warning');
    if (state === 'error' && !status && !warning) {
      warning = document.createElement('p');
      warning.id = 'preferences-sync-warning'; warning.className = 'sync-warning';
      warning.setAttribute('role', 'status'); document.querySelector('main')?.prepend(warning);
    }
    if (warning) {
      if (state === 'error') warning.textContent = message;
      else if (state === 'saved') warning.remove();
    }
  }
  function apply(values, restore = false) {
    const datasetNames = { voice: 'voice', speech_rate: 'speechRate', browser_voice: 'browserVoice', sound: 'sound', volume: 'volume', keyboard_open: 'keyboardOpen' };
    for (const [key, value] of Object.entries(values)) {
      if (datasetNames[key]) document.body.dataset[datasetNames[key]] = String(value);
      if (key === 'theme') {
        document.documentElement.dataset.theme = value;
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.content = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
      }
      if (key === 'name') {
        const name = String(value).trim() || 'Explorateur';
        document.querySelectorAll('.profile strong').forEach(node => { node.textContent = name; });
        document.querySelectorAll('.avatar, .mini-avatar').forEach(node => { node.textContent = name[0].toUpperCase(); });
      }
      if (key === 'browser_voice') {
        const select = document.getElementById('browser-voice');
        if (select) {
          select.dataset.saved = value;
          if (restore && ![...select.options].some(option => option.value === value)) select.add(new Option('Voix enregistrée', value));
        }
      }
    }
    if (restore && form) form.querySelectorAll('[name]').forEach(control => {
      if (!(control.name in values)) return;
      const value = values[control.name];
      if (control.type === 'checkbox') control.checked = Number(value) === 1;
      else if (control.type === 'radio') control.checked = control.value === value;
      else control.value = value;
    });
  }
  async function flush() {
    clearTimeout(timer);
    if (saving || !Object.keys(pending).length) return;
    saving = true;
    const batch = { ...pending };
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let success = false;
    notify('Enregistrement…', 'saving');
    try {
      const response = await fetch(endpoint, {
        method: 'POST', credentials: 'same-origin', keepalive: true, signal: controller.signal,
        body: new URLSearchParams({ csrf: document.querySelector('meta[name="csrf-token"]').content, ...batch }),
      });
      if (!response.ok) throw new Error(response.status === 401 ? 'expired' : 'save');
      const result = await response.json();
      if (result.saved !== true) throw new Error('save');
      for (const [key, value] of Object.entries(batch)) if (pending[key] === value) delete pending[key];
      remember(); success = true;
      if (!Object.keys(pending).length) notify('✓ Modifications enregistrées.', 'saved');
    } catch (error) {
      notify(error.message === 'expired' ? 'Session expirée. Reconnecte-toi pour enregistrer les réglages.' : 'Réglages appliqués ici, mais pas encore synchronisés. Nouvelle tentative automatique dès que la connexion revient.', 'error');
    } finally {
      clearTimeout(timeout); saving = false;
      if (Object.keys(pending).length) timer = setTimeout(flush, success ? 0 : 10000);
    }
  }
  window.slovoSavePreferences = values => {
    const allowed = Object.fromEntries(Object.entries(values).filter(([key]) => fields.has(key)));
    if (!Object.keys(allowed).length) return;
    apply(allowed); pending = { ...pending, ...allowed }; remember();
    notify('Modification appliquée · enregistrement…', 'saving');
    clearTimeout(timer); timer = setTimeout(flush, 300);
  };
  if (form) {
    const changed = event => {
      const control = event.target;
      if (!fields.has(control.name) || control.type === 'radio' && !control.checked) return;
      window.slovoSavePreferences({ [control.name]: control.type === 'checkbox' ? Number(control.checked) : control.value });
    };
    form.addEventListener('change', changed);
    form.addEventListener('input', event => { if (event.target.name === 'name') changed(event); });
    form.addEventListener('submit', event => { event.preventDefault(); flush(); });
  }
  retry?.addEventListener('click', flush);
  window.addEventListener('online', flush);
  window.addEventListener('pagehide', () => { remember(); flush(); });
  if (Object.keys(pending).length) { apply(pending, true); flush(); }
})();
