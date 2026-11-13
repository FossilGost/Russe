// Run with Node, or require this module and await its exported function.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/speech.js'), 'utf8');

function setup({ voice = 'svetlana', failure = false, delayed = false, volume = 1, listening = false } = {}) {
  const events = {}, fetches = [], players = [], spoken = [], revoked = [], status = { textContent: '' };
  let release;
  const gate = delayed ? new Promise(resolve => { release = resolve; }) : Promise.resolve();
  const buttons = ['normal', 'slow'].map(rate => ({
    dataset: { speak: 'ко́фе', audioUrl: '/audio/1', ...(rate === 'slow' ? { speechRate: 'slow' } : {}) },
    setAttribute() {}, removeAttribute() {}, closest() { return true; },
  }));
  const voices = [{ lang: 'ru-RU', name: 'Russian voice A', voiceURI: 'A' }];
  if (listening) {
    buttons.forEach(button => { button.dataset.speak = ''; button.dataset.listeningTextUrl = '/listening/run/0/text'; });
    buttons[0].dataset.autoListen = '1';
  }
  class Audio {
    constructor(url) { this.src = url; this.plays = []; players.push(this); }
    load() {} pause() {} removeAttribute(name) { if(name==='src') delete this.src; }
    play() { this.plays.push({ rate: this.playbackRate, pitch: this.preservesPitch }); return Promise.resolve(); }
  }
  class TestURL extends URL {
    static createObjectURL() { return 'blob:recording-'+players.length; }
    static revokeObjectURL(url) { revoked.push(url); }
  }
  vm.runInNewContext(source, {
    window: { slovoVolume: { get: () => volume }, speechSynthesis: { getVoices: () => voices, cancel() {},
      speak: utterance => spoken.push(utterance), addEventListener() {}, removeEventListener() {} }, addEventListener() {} },
    document: {
      body: { dataset: { voice, speechRate: 'normal' } },
      getElementById: id => id === 'speech-status' ? status : null,
      querySelectorAll: selector => selector === '[data-audio-url]' ? buttons : [],
      querySelector: selector => listening && selector === '[data-auto-listen]' ? buttons[0] : null,
      addEventListener: (event, fn) => { events[event] = fn; },
    },
    URL: TestURL, location: { origin: 'http://localhost' }, Audio, AbortController,
    SpeechSynthesisUtterance: function(text) { this.text = text; },
    setTimeout: () => 1, clearTimeout() {},
    fetch: async url => { fetches.push(url); await gate; return { ok: !failure, blob: async () => ({}), json: async () => ({text:'ко́фе'}) }; },
  });
  return { buttons, fetches, players, spoken, status, voices, release, revoked,
    visit: index => { buttons.forEach(button => { button.dataset.audioUrl='/audio/'+index; }); events['slovo:question'](); },
    setVolume: value => { volume = value; events['slovo:volume'](); },
    click: index => events.click({ target: { closest: () => buttons[index] } }) };
}
async function flush() { for (let i = 0; i < 30; i++) await Promise.resolve(); }

module.exports = async function run() {
  const ready = setup();
  await flush();
  assert.equal(ready.fetches.length, 1, 'both speeds preload a single recording');
  assert.equal(new URL(ready.fetches[0]).searchParams.get('rate'), 'normal');
  ready.click(0);
  assert.equal(ready.players[0].plays.length, 1, 'ready audio starts during the click handler');
  ready.click(1);
  assert.equal(ready.players.length, 1, 'slow reuses the same audio player and voice');
  assert.equal(ready.players[0].plays[0].rate, 1, 'normal pronunciation is unchanged');
  assert.equal(ready.players[0].plays[1].rate, 0.72);
  assert.ok(ready.players[0].plays.every(play => play.pitch));
  assert.equal(ready.fetches.length, 1, 'replays need no new network request');
  await flush();

  const delayed = setup({ delayed: true });
  delayed.click(0); delayed.click(1); delayed.release(); await flush();
  assert.equal(delayed.players[0].plays.length, 1, 'an interrupted request cannot start later');
  assert.equal(delayed.players[0].plays[0].rate, 0.72);
  assert.equal(delayed.fetches.length, 1, 'clicking during preload shares its request');

  const offline = setup({ failure: true });
  await flush(); offline.click(1); await flush();
  assert.equal(offline.spoken.length, 0, 'failure does not silently change the selected voice');
  assert.match(offline.status.textContent, /indisponible/);

  const browser = setup({ voice: 'browser' });
  browser.click(0); await flush();
  browser.voices.unshift({ lang: 'ru-RU', name: 'Natural new voice', voiceURI: 'B' });
  browser.click(1); await flush();
  assert.equal(browser.spoken[0].voice, browser.spoken[1].voice, 'browser voice stays fixed across speeds');
  assert.ok(browser.spoken[1].rate < browser.spoken[0].rate);
  assert.equal(browser.fetches.length, 0);
  const quiet = setup({ volume: 0.3 });
  await flush(); quiet.click(0);
  assert.equal(quiet.players[0].volume, 0.3);
  quiet.setVolume(0);
  assert.equal(quiet.players[0].volume, 0, 'mute applies to the current recording');
  quiet.click(1);
  assert.equal(quiet.players[0].volume, 0, 'slow playback keeps the volume');
  const quietBrowser = setup({ voice: 'browser', volume: 0.4 });
  quietBrowser.click(0); await flush();
  assert.equal(quietBrowser.spoken[0].volume, 0.4);
  const dictation = setup({ listening: true });
  await flush();
  assert.equal(dictation.players[0].plays.length, 1, 'listening question automatically plays its recording');
  dictation.click(1); await flush();
  assert.equal(dictation.players[0].plays[1].rate, 0.72, 'dictation can replay slowly');
  const browserDictation = setup({ listening: true, voice: 'browser' });
  await flush();
  assert.equal(browserDictation.spoken[0].text, 'кофе', 'browser voice obtains the hidden listening text on demand');
  assert.equal(browserDictation.buttons[0].dataset.speak, '', 'the answer stays out of HTML attributes');
  assert.equal(browserDictation.fetches[0], '/listening/run/0/text');
  const longSession=setup();
  await flush();
  for(let word=2;word<=40;word++){longSession.visit(word);await flush();}
  assert.ok(longSession.players.filter(player=>player.src).length<=12,'long sessions keep at most twelve prepared recordings');
  assert.ok(longSession.revoked.length>=28,'old recordings release their audio source and blob URL');
  longSession.click(1);await flush();
  assert.equal(longSession.fetches.length,40,'slow replay still reuses the most recent cached recording');
  return 'Audio checks passed: shared recording, immediate cached playback, interruption, failure, stable browser voice.';
};
if (require.main === module) module.exports().then(console.log).catch(error => { console.error(error); process.exitCode = 1; });
