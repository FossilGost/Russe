/* One volume for pronunciation and feedback, kept across visits. */
(() => {
  const slider = document.getElementById('app-volume');
  const output = document.getElementById('volume-value');
  if (!slider) return;
  let level = 1;
  const account = document.body.dataset.userId;
  const storageKey = account ? `slovo:${account}:volume` : 'slovo:volume';
  try {
    const saved = account ? String(Number(document.body.dataset.volume) / 100) : localStorage.getItem(storageKey);
    if (saved !== null && saved.trim() !== '' && Number.isFinite(Number(saved))) {
      level = Math.max(0, Math.min(1, Number(saved)));
    }
  } catch (_) { /* The control also works without storage. */ }
  function display() {
    slider.value = Math.round(level * 100);
    slider.setAttribute('aria-valuetext', level === 0 ? 'Muet' : `${slider.value} %`);
    if (output) output.textContent = `${slider.value} %`;
  }
  window.slovoVolume = { get: () => level };
  slider.addEventListener('input', () => {
    level = Math.max(0, Math.min(1, Number(slider.value) / 100));
    display();
    try { localStorage.setItem(storageKey, String(level)); } catch (_) { /* Optional persistence. */ }
    window.slovoSavePreferences?.({ volume: Math.round(level * 100) });
    document.dispatchEvent(new CustomEvent('slovo:volume', { detail: level }));
  });
  display();
})();
