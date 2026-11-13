/* Preloaded Russian recordings shared across speeds, with a stable voice. */
(() => {
  const synthesis = window.speechSynthesis;
  const voiceSelect = document.getElementById('voice');
  const browserSelect = document.getElementById('browser-voice');
  const rateSelect = document.getElementById('speech-rate');
  const status = document.getElementById('speech-status');
  const volume = () => window.slovoVolume?.get() ?? 1;
  let activeAudio = null, requestNumber = 0, utterance = null, browserVoice = null;
  const prepared = new Map();
  const pending = [];
  const queued = new Set();
  let preparing = 0;
  const MAX_RECORDINGS = 12, MAX_PENDING = 6;
  const selectedVoice = () => voiceSelect?.value || document.body.dataset.voice || 'svetlana';
  const sayStatus = text => { if (status) status.textContent = text; };
  const russianVoices = () => (synthesis?.getVoices() || []).filter(v => /^ru(?:[-_]|$)/i.test(v.lang));
  const rankVoice = v => (/natural|neural|online/i.test(v.name) ? 100 : 0) + (/google|microsoft/i.test(v.name) ? 10 : 0) + (v.default ? 1 : 0);
  const rankedVoices = () => russianVoices().sort((a, b) => rankVoice(b) - rankVoice(a) || a.name.localeCompare(b.name));

  // Prepare visible words while the learner answers, without playing them.
  // Translation exercises keep their Russian answer hidden until validation.
  function audioKey(button, voice) {
    const url = new URL(button.dataset.audioUrl, location.origin);
    // One recording for both buttons: slow playback preserves its pitch/voice.
    url.searchParams.set('voice', voice); url.searchParams.set('rate', 'normal');
    return url.href;
  }
  function releaseEntry(key, entry) {
    entry.disposed = true; entry.controller.abort();
    if (entry.audio) { entry.audio.pause(); entry.audio.onended = null; entry.audio.removeAttribute('src'); entry.audio.load(); }
    if (entry.url) URL.revokeObjectURL(entry.url);
    prepared.delete(key);
  }
  function trimRecordings(keep) {
    for (const [key, entry] of prepared) {
      if (prepared.size <= MAX_RECORDINGS) break;
      if (key !== keep && !(entry.audio && entry.audio === activeAudio)) releaseEntry(key, entry);
    }
  }
  function prepareAudio(button, voice) {
    const key = audioKey(button, voice);
    if (prepared.has(key)) {
      const entry = prepared.get(key);
      prepared.delete(key); prepared.set(key, entry);
      return entry;
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    const entry = { controller, promise: null, audio: null, url: null };
    entry.promise = fetch(key, { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error('Speech unavailable');
      return response.blob();
    }).then(blob => {
      if (entry.disposed) throw new Error('Recording released');
      entry.url = URL.createObjectURL(blob);
      entry.audio = new Audio(entry.url);
      entry.audio.preload = 'auto';
      entry.audio.preservesPitch = true;
      entry.audio.load();
      return entry.audio;
    }).catch(error => {
      if (prepared.get(key) === entry) prepared.delete(key);
      throw error;
    }).finally(() => clearTimeout(timeout));
    prepared.set(key, entry);
    trimRecordings(key);
    return entry;
  }

  function drainQueue() {
    while (!document.hidden && preparing < 2 && pending.length) {
      const { button, voice, key } = pending.shift();
      queued.delete(key);
      if (button.isConnected === false) continue;
      preparing += 1;
      prepareAudio(button, voice).promise.catch(() => {}).finally(() => {
        preparing -= 1; drainQueue();
      });
    }
  }
  function queueAudio(button) {
    const voice = selectedVoice();
    if (voice === 'browser') return;
    const key = audioKey(button, voice);
    if (prepared.has(key) || queued.has(key)) return;
    if (pending.length >= MAX_PENDING) return;
    queued.add(key); pending.push({ button, voice, key }); drainQueue();
  }
  const observer = window.IntersectionObserver ? new IntersectionObserver(entries => {
    entries.filter(entry => entry.isIntersecting).forEach(entry => {
      queueAudio(entry.target); observer.unobserve(entry.target);
    });
  }, { rootMargin: '100px' }) : null;
  function preloadVisibleAudio() {
    if (selectedVoice() === 'browser' || document.hidden) return;
    // Never expose the answer to a translation exercise before validation.
    document.querySelectorAll('[data-audio-url]').forEach(button => {
      if (button.dataset.speechRate === 'slow') return;
      if (button.closest('.practice-card, .voice-preview-actions')) queueAudio(button);
      else if (observer) observer.observe(button);
    });
  }

  function populateVoices() {
    if (!browserSelect) return;
    const saved = browserSelect.value || browserSelect.dataset.saved || '';
    browserSelect.replaceChildren(new Option('Automatique · meilleure voix disponible', ''));
    const voices = rankedVoices();
    voices.forEach(v => browserSelect.add(new Option(v.name + (v.localService ? ' · locale' : ' · en ligne'), v.voiceURI)));
    if (saved && !voices.some(v => v.voiceURI === saved)) browserSelect.add(new Option('Voix enregistrée · indisponible sur cet appareil', saved));
    browserSelect.value = saved;
  }
  function waitForVoices() {
    if (!synthesis || russianVoices().length) return Promise.resolve();
    return new Promise(resolve => {
      const done = () => { clearTimeout(timeout); synthesis.removeEventListener('voiceschanged', onChange); resolve(); };
      const onChange = () => { if (russianVoices().length) done(); };
      const timeout = setTimeout(done, 1800);
      synthesis.addEventListener('voiceschanged', onChange);
      synthesis.getVoices();
    });
  }
  function stop() {
    requestNumber += 1;
    if (activeAudio) { activeAudio.pause(); activeAudio.currentTime = 0; activeAudio = null; }
    synthesis?.cancel(); utterance = null;
    document.querySelectorAll('[data-speak][aria-busy]').forEach(button => button.removeAttribute('aria-busy'));
  }
  function markPlayed(button) {
    if (button.dataset.autoSpeak) {
      try { sessionStorage.setItem('slovo:last-spoken-answer', button.dataset.autoSpeak); } catch (_) { /* Storage can be disabled. */ }
    }
  }
  function finished(button, id) {
    if (id !== requestNumber) return;
    sayStatus('Lecture terminée.');
    const next = document.querySelector('.next-form[data-auto-next]');
    if (button.dataset.autoSpeak && next && !next.dataset.advancing) {
      next.dataset.advancing = '1';
      next.requestSubmit();
    }
  }
  async function browserSpeak(text, rate, id, button) {
    if (!synthesis) { sayStatus('La lecture vocale n’est pas disponible dans ce navigateur.'); return; }
    await waitForVoices();
    if (id !== requestNumber) return;
    const selected = browserSelect ? browserSelect.value : document.body.dataset.browserVoice;
    const voice = browserVoice || rankedVoices().find(v => v.voiceURI === selected) || rankedVoices()[0];
    if (!voice) { sayStatus('Aucune voix russe disponible sur cet appareil. Choisis Svetlana ou Dmitry avec une connexion Internet.'); return; }
    browserVoice = voice;
    utterance = new SpeechSynthesisUtterance(text.replace(/\u0301/g, ''));
    utterance.lang = 'ru-RU'; utterance.voice = voice; utterance.rate = { slow: 0.75, normal: 0.9, fast: 1 }[rate] || 0.9;
    utterance.pitch = 1;
    utterance.volume = volume();
    utterance.onstart = () => {
      if (id !== requestNumber) return;
      markPlayed(button);
      sayStatus('Lecture : ' + voice.name);
    };
    utterance.onerror = event => {
      if (id === requestNumber && !['canceled', 'interrupted'].includes(event.error)) {
        sayStatus(event.error === 'not-allowed' ? 'Ton navigateur bloque la lecture automatique. Clique sur « Écouter » pour entendre le mot.' : 'Lecture impossible. Essaie une autre voix dans les préférences.');
      }
    };
    utterance.onend = () => finished(button, id);
    synthesis.speak(utterance);
  }
  async function speak(button) {
      stop();
      const id = requestNumber;
      const selected = selectedVoice();
      const rate = button.dataset.speechRate || rateSelect?.value || document.body.dataset.speechRate || 'normal';
      if (selected === 'browser' || !button.dataset.audioUrl) {
        let text = button.dataset.speak;
        if (button.dataset.listeningTextUrl) {
          try {
            const response = await fetch(button.dataset.listeningTextUrl, { cache: 'no-store' });
            if (!response.ok) throw new Error('Listening session unavailable');
            text = (await response.json()).text;
          } catch (_) {
            if (id === requestNumber) sayStatus('Lecture indisponible. Réessaie avec Écouter.');
            return;
          }
        }
        if (id === requestNumber) await browserSpeak(text, rate, id, button);
        return;
      }
      const entry = prepareAudio(button, selected);
      button.setAttribute('aria-busy', 'true');
      if (!entry.audio) sayStatus('Première préparation de cette voix…');
      try {
        // A ready recording starts in the click handler, without another fetch.
        const audio = entry.audio || await entry.promise;
        if (id !== requestNumber) return;
        activeAudio = audio;
        activeAudio.currentTime = 0;
        activeAudio.preservesPitch = true;
        activeAudio.volume = volume();
        activeAudio.playbackRate = { slow: 0.72, normal: 1, fast: 1 / 0.9 }[rate] || 1;
        activeAudio.onended = () => finished(button, id);
        await activeAudio.play();
        if (id === requestNumber) {
          markPlayed(button);
          sayStatus('Lecture : ' + (selected === 'dmitry' ? 'Dmitry' : 'Svetlana'));
        }
      } catch (error) {
        if (id === requestNumber) {
          if (error.name === 'NotAllowedError') {
            sayStatus('Ton navigateur bloque la lecture automatique. Clique sur « Écouter » pour entendre le mot.');
          } else {
            sayStatus('Cette voix est indisponible. Réessaie ou choisis la voix du navigateur dans les préférences.');
          }
        }
      } finally {
        if (id === requestNumber) button.removeAttribute('aria-busy');
      }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-speak]');
    if (button) speak(button);
  });
  document.querySelectorAll('.stop-speech').forEach(button => button.addEventListener('click', () => { stop(); sayStatus('Lecture arrêtée.'); }));
  [voiceSelect, rateSelect, browserSelect].filter(Boolean).forEach(select => select.addEventListener('change', () => {
    if (select === browserSelect) browserSelect.dataset.saved = browserSelect.value;
    browserVoice = null;
    stop(); pending.length = 0; queued.clear(); observer?.disconnect();
    preloadVisibleAudio(); sayStatus('Clique sur « Essayer cette voix » pour écouter ce réglage.');
  }));
  window.addEventListener('pagehide', () => {
    stop();
    pending.length = 0; queued.clear(); observer?.disconnect();
    prepared.forEach((entry,key) => releaseEntry(key,entry));
  });
  synthesis?.addEventListener('voiceschanged', populateVoices);
  populateVoices();
  preloadVisibleAudio();
  // Every validated answer reads the Russian correction, whether right or wrong.
  function autoSpeakCorrection() {
    const automatic = document.querySelector('[data-auto-speak]');
    if (!automatic) return;
    let alreadyPlayed = false;
    try { alreadyPlayed = sessionStorage.getItem('slovo:last-spoken-answer') === automatic.dataset.autoSpeak; } catch (_) { /* Try playback without storage. */ }
    if (!alreadyPlayed) speak(automatic);
  }
  document.addEventListener('slovo:correction', () => { preloadVisibleAudio(); autoSpeakCorrection(); });
  document.addEventListener('slovo:transition', stop);
  document.addEventListener('slovo:volume', () => {
    if (activeAudio) activeAudio.volume = volume();
    if (utterance) utterance.volume = volume();
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { preloadVisibleAudio(); drainQueue(); }
  });
  function autoListen() {
    const button = document.querySelector('[data-auto-listen]');
    if (button) speak(button);
  }
  document.addEventListener('slovo:question', () => { preloadVisibleAudio(); autoListen(); });
  autoSpeakCorrection();
  autoListen();
})();
