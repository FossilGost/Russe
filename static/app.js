/* Progressive enhancement: exercises and persistence also work without JS. */
(() => {
  const account = document.body.dataset.userId;
  const key = account ? `slovo:${account}:keyboard-open` : 'slovo:keyboard-open';
  let current = account ? document.body.dataset.keyboardOpen : null;
  function restore() {
    const keyboard = document.querySelector('.keyboard-wrap');
    if (!keyboard) return;
    try {
      const saved = current ?? localStorage.getItem(key);
      if (saved === '1' || saved === '0') keyboard.open = saved === '1';
    } catch (_) { /* The keyboard remains usable when storage is unavailable. */ }
  }
  const remember = () => {
    const keyboard = document.querySelector('.keyboard-wrap');
    if (!keyboard) return;
    const next = keyboard.open ? '1' : '0';
    if (next === current) return;
    current = next;
    try { localStorage.setItem(key, current); } catch (_) { /* Optional persistence. */ }
    window.slovoSavePreferences?.({ keyboard_open: Number(current) });
  };
  document.addEventListener('toggle', event => {
    if (event.target.matches('.keyboard-wrap')) remember();
  }, true);
  document.addEventListener('slovo:transition', remember);
  document.addEventListener('slovo:question', restore);
  window.addEventListener('pagehide', remember);
  restore();
})();
document.addEventListener('click', event => {
    const button = event.target.closest('[data-key]');
    if (!button || button.disabled) return;
    const input = document.getElementById('russian-input');
    if (!input || input.readOnly) return;
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? start;
    const backspace = button.dataset.key === 'backspace';
    const from = backspace && start === end ? Math.max(0, start - 1) : start;
    input.setRangeText(backspace ? '' : button.dataset.key, from, end, 'end');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
});
document.querySelectorAll('input[name="theme"]').forEach(input => {
  input.addEventListener('change', () => {
    document.documentElement.dataset.theme = input.value;
    const status = document.getElementById('theme-preview-status');
    if (status) status.textContent = 'Thème appliqué.';
    updateBrowserColor();
  });
});
function updateBrowserColor() {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
}
updateBrowserColor();
document.addEventListener('keydown', event => {
  if ((/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && document.activeElement.type !== 'radio') || event.ctrlKey || event.altKey || event.metaKey) return;
  if (/^[1-4]$/.test(event.key)) {
    const options = document.querySelectorAll('.choice input');
    const option = options[Number(event.key) - 1];
    if (option) { option.checked = true; option.focus(); }
  }
});
