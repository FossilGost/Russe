/* Keep the entire practice session in one document, including the next word. */
(() => {
  if (!document.querySelector('.practice-card') || !window.fetch || !window.DOMParser) return;
  let input, form, timer, controller, revision = 0, composing = false, submitting = false;
  const notice = text => {
    const status = document.getElementById('practice-status');
    if (status) status.textContent = text;
  };
  function bindQuestion() {
    revision += 1; clearTimeout(timer); controller?.abort(); composing = false;
    input = document.getElementById('russian-input');
    form = document.getElementById('answer-form');
    if (input && form && !form.querySelector('[name="auto_advance"]')) {
      const advance = document.createElement('input');
      advance.type = 'hidden'; advance.name = 'auto_advance'; advance.value = '1'; form.append(advance);
    }
    input?.addEventListener('input', schedule);
    input?.addEventListener('compositionstart', () => {
      composing = true; revision += 1; clearTimeout(timer); controller?.abort();
    });
    input?.addEventListener('compositionend', () => { composing = false; schedule(); });
  }
  function schedule() {
    revision += 1; clearTimeout(timer); controller?.abort();
    if (composing || submitting || !input?.value.trim()) return;
    const current = revision, currentForm = form;
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        const response = await fetch(currentForm.dataset.checkUrl, {
          method: 'POST', body: new FormData(currentForm), signal: controller.signal,
        });
        if (response.status === 401) { window.location.assign('/login'); return; }
        if (!response.ok) return;
        const result = await response.json();
        if (current === revision && !composing && !submitting && result.matches) currentForm.requestSubmit();
      } catch (_) { /* Enter and the submit button remain available. */ }
    }, 180);
  }
  function render(html) {
    const page = new DOMParser().parseFromString(html, 'text/html');
    const card = page.querySelector('.practice-card'), result = page.querySelector('.result-card');
    if (!card && !result) throw new Error('Practice response missing');
    document.dispatchEvent(new Event('slovo:transition'));
    if (card && document.querySelector('.practice-card')) {
      for (const selector of ['.practice-card', '.practice-top', '.session-progress']) {
        const existing = document.querySelector(selector), replacement = page.querySelector(selector);
        if (existing && replacement) existing.replaceWith(replacement);
      }
    } else {
      document.getElementById('main').replaceChildren(...page.getElementById('main').childNodes);
    }
    const stats = page.querySelector('.top-stats');
    if (stats) document.querySelector('.top-stats')?.replaceWith(stats);
    document.title = page.title;
    notice('');
    const speechStatus = document.getElementById('speech-status');
    if (speechStatus) speechStatus.textContent = '';
    bindQuestion(); submitting = false;
    document.dispatchEvent(new Event('slovo:question'));
    if (document.querySelector('[data-feedback-id]')) {
      document.querySelector('.next-form button')?.focus({ preventScroll: true });
      document.dispatchEvent(new Event('slovo:correction'));
    } else {
      const focus = input || document.querySelector('.choice input') || document.querySelector('.result-card h1');
      if (focus && !focus.matches('input')) focus.setAttribute('tabindex', '-1');
      focus?.focus({ preventScroll: true });
    }
  }
  async function request(url, options) {
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 10000);
    try {
      const response = await fetch(url, {
        ...options, headers: { 'X-Slovo-Transition': '1' }, signal: abort.signal, cache: 'no-store',
      });
      if (response.status === 401) {
        const expired = new Error('Session expired'); expired.sessionExpired = true; throw expired;
      }
      if (!response.ok) throw new Error('Practice request failed');
      return await response.text();
    } finally { clearTimeout(timeout); }
  }
  document.addEventListener('submit', async event => {
    const submitted = event.target;
    if (!submitted.matches('#answer-form, .next-form')) return;
    event.preventDefault();
    if (submitting || composing) return;
    submitting = true; revision += 1; clearTimeout(timer); controller?.abort();
    const data = new FormData(submitted);
    const controls = [...submitted.querySelectorAll('button, input[type="radio"]')], currentInput = input;
    controls.forEach(control => { control.disabled = true; });
    if (currentInput) currentInput.readOnly = true;
    submitted.setAttribute('aria-busy', 'true');
    notice(submitted.matches('.next-form') ? 'Mot suivant…' : 'Validation…');
    try {
      render(await request(submitted.action, { method: 'POST', body: data }));
    } catch (error) {
      if (error.sessionExpired) { window.location.assign('/login'); return; }
      // Read the server state: the POST may already have succeeded.
      try { render(await request('/practice')); }
      catch (error) {
        if (error.sessionExpired) { window.location.assign('/login'); return; }
        submitting = false;
        controls.forEach(control => { control.disabled = false; });
        if (currentInput) currentInput.readOnly = false;
        submitted.removeAttribute('aria-busy');
        notice('Connexion interrompue. Réessaie avec Valider ou Continuer ; ta réponse ne sera pas comptée deux fois.');
        (currentInput || submitted.querySelector('button'))?.focus({ preventScroll: true });
      }
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Enter' && event.repeat && document.querySelector('.practice-card')) event.preventDefault();
  });
  bindQuestion();
})();
