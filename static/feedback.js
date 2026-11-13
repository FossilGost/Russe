/* Local synthesized cues: no download, no effect on scoring or pronunciation. */
(() => {
  let context = null, master = null, idleTimer;
  function restAudio() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { if (context?.state === 'running') context.suspend().catch(() => {}); }, 1200);
  }
  const volume = () => window.slovoVolume?.get() ?? 1;
  document.addEventListener('slovo:volume', () => {
    if (master) master.gain.value = volume();
  });
  const seen = new Set();
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function unlock() {
    if (document.body.dataset.sound !== '1') return;
    try {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!Context) return;
      context ??= new Context();
      if (!master) {
        master = context.createGain();
        master.gain.value = volume();
        master.connect(context.destination);
      }
      if (context.state === 'suspended') context.resume().catch(() => {});
      restAudio();
    } catch (_) { /* Silent browsers keep visual feedback. */ }
  }
  document.addEventListener('pointerdown', unlock, { passive: true });
  document.addEventListener('keydown', unlock);
  document.addEventListener('submit', unlock);

  function sound(correct, combo) {
    if (document.body.dataset.sound !== '1' || context?.state !== 'running') return;
    try {
      const notes = correct ? (combo >= 5 ? [659.25, 830.61, 987.77, 1318.51] :
        combo >= 3 ? [523.25, 659.25, 783.99, 1046.5] : [523.25, 659.25, 783.99]) : [220, 164.81];
      notes.forEach((frequency, index) => {
        const oscillator = context.createOscillator(), gain = context.createGain();
        oscillator.type = correct ? 'sine' : 'triangle';
        oscillator.frequency.value = frequency;
        oscillator.connect(gain); gain.connect(master);
        const start = context.currentTime + index * 0.075;
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(correct ? 0.075 : 0.045, start + 0.012);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.17);
        oscillator.start(start); oscillator.stop(start + 0.18);
        oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
      });
      restAudio();
    } catch (_) { /* Audio is optional. */ }
  }

  function celebrate(feedback, combo) {
    if (reducedMotion.matches) return;
    const card = feedback.closest('.practice-card');
    const burst = document.createElement('div');
    burst.className = 'reward-burst'; burst.setAttribute('aria-hidden', 'true');
    const colors = ['#e8b94e', '#70b887', '#b399dc', '#f08d72'];
    for (let i = 0; i < (combo >= 3 ? 26 : 16); i++) {
      const particle = document.createElement('i');
      const angle = Math.PI * 2 * i / (combo >= 3 ? 26 : 16);
      const distance = 65 + Math.random() * 80;
      particle.style.setProperty('--dx', `${Math.cos(angle) * distance}px`);
      particle.style.setProperty('--dy', `${Math.sin(angle) * distance - 35}px`);
      particle.style.setProperty('--spin', `${Math.random() * 540}deg`);
      particle.style.background = colors[i % colors.length];
      burst.append(particle);
    }
    const xp = document.createElement('span');
    xp.className = 'floating-xp'; xp.textContent = `+${feedback.dataset.xp} XP`;
    burst.append(xp); card?.append(burst);
    setTimeout(() => burst.remove(), 1200);
  }

  function show() {
    const feedback = document.querySelector('[data-feedback-id]');
    if (!feedback || seen.has(feedback.dataset.feedbackId)) return;
    const id = feedback.dataset.feedbackId;
    seen.add(id);
    if (seen.size > 32) seen.delete(seen.values().next().value);
    try {
      if (sessionStorage.getItem('slovo:last-feedback') === id) return;
      sessionStorage.setItem('slovo:last-feedback', id);
    } catch (_) { /* In-memory deduplication remains available. */ }
    const correct = feedback.dataset.correct === 'yes';
    const combo = Number(feedback.dataset.combo) || 0;
    feedback.closest('.practice-card')?.classList.add(correct ? 'answer-success' : 'answer-error');
    if (correct) celebrate(feedback, combo);
    sound(correct, combo);
  }
  document.addEventListener('slovo:correction', show);
  show();
})();
