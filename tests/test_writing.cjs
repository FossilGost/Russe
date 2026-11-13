const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

module.exports = async function run() {
  const handlers = {}, timers = new Map(), calls = [], emitted = [], pages = new Map();
  let clock = 0, current, focused, fail = false, pending;
  class Node {
    constructor(kind) { this.kind = kind; this.dataset = {}; this.events = {}; this.children = []; this.controls = []; }
    matches(selector) { return selector.split(', ').includes(this.kind) || selector === 'input' && this.kind === '#russian-input'; }
    addEventListener(type, listener) { this.events[type] = listener; }
    setAttribute() {} removeAttribute() {}
    focus() { focused = this; }
    append(child) { this.children.push(child); }
    querySelector(selector) {
      if (selector === '[name="auto_advance"]') return this.children.find(child => child.name === 'auto_advance');
      return selector === 'button' ? this.controls[0] : null;
    }
    querySelectorAll() { return this.controls; }
    replaceWith(replacement) {
      if (this.kind === '.practice-card') current = replacement.page;
    }
    requestSubmit() { pending = submit(this); }
  }
  function page(name, stage) {
    const p = { title: name, nodes: {}, querySelector(selector) { return this.nodes[selector] || null; },
      getElementById(id) { return this.querySelector('#'+id); } };
    for (const kind of ['.top-stats', '#practice-status', '#speech-status', '#main', stage === 'result' ? '.result-card' : '.practice-card']) {
      const node = new Node(kind); node.page = p; p.nodes[kind] = node;
    }
    p.nodes['#main'].childNodes = [p];
    if (stage === 'question') {
      const form = new Node('#answer-form'), input = new Node('#russian-input');
      form.action = '/answer'; form.dataset.checkUrl = '/check-answer'; form.controls = [new Node('button')];
      input.value = '';
      p.nodes['#answer-form'] = form; p.nodes['#russian-input'] = input;
    } else if (stage === 'correction') {
      const form = new Node('.next-form'); form.action = '/next'; form.controls = [new Node('button')];
      p.nodes['.next-form'] = form; p.nodes['.next-form button'] = form.controls[0];
      p.nodes['[data-feedback-id]'] = new Node('feedback');
    } else p.nodes['.result-card h1'] = new Node('h1');
    pages.set(name, p); return p;
  }
  const q1 = page('q1', 'question'), c1 = page('c1', 'correction');
  const q2 = page('q2', 'question'), c2 = page('c2', 'correction'), result = page('result', 'result');
  current = q1;
  const replies = ['c1', 'q2', 'c2', 'result'];
  const document = {
    querySelector: selector => current.querySelector(selector),
    getElementById: id => {
      if (id === 'main') return { replaceChildren: p => { current = p; } };
      return current.getElementById(id);
    },
    createElement: kind => new Node(kind),
    addEventListener: (type, listener) => { handlers[type] = listener; },
    dispatchEvent: event => { emitted.push(event.type); },
  };
  const submit = form => handlers.submit({ target: form, preventDefault() {} });
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/writing.js'), 'utf8'), {
    document, window: { fetch: true, DOMParser: true }, AbortController,
    DOMParser: class { parseFromString(name) { return pages.get(name); } },
    Event: class { constructor(type) { this.type = type; } },
    FormData: class { constructor(form) { this.form = form; } },
    setTimeout: (fn, delay) => { timers.set(++clock, { fn, delay }); return clock; },
    clearTimeout: id => timers.delete(id),
    location: { assign() { assert.fail('The practice document must not navigate'); } },
    fetch: async (url, options = {}) => {
      calls.push({ url, options });
      if (fail) throw new Error('Offline');
      if (url === '/check-answer') return { ok: true, json: async () => ({ matches: true }) };
      return { ok: true, text: async () => replies.shift() };
    },
  });
  assert.equal(q1.nodes['#answer-form'].children[0].name, 'auto_advance');
  await submit(q1.nodes['#answer-form']);
  assert.equal(current, c1);
  assert.equal(focused, c1.nodes['.next-form button']);
  await submit(c1.nodes['.next-form']);
  assert.equal(current, q2, 'next word stays in the same document');
  assert.equal(focused, q2.nodes['#russian-input'], 'typing can resume immediately');
  assert.equal(q2.nodes['#answer-form'].children[0].name, 'auto_advance');
  const input = q2.nodes['#russian-input'];
  input.value = 'answer'; input.events.input();
  const check = [...timers.values()].find(timer => timer.delay === 180);
  assert.ok(check, 'live validation is rebound on the second word');
  await check.fn(); await pending;
  assert.equal(current, c2);
  await submit(c2.nodes['.next-form']);
  assert.equal(current, result, 'results also render without navigation');
  assert.equal(emitted.filter(event => event === 'slovo:correction').length, 2);
  assert.equal(emitted.filter(event => event === 'slovo:question').length, 4);
  assert.deepEqual(calls.filter(call => call.options.method === 'POST').map(call => call.url),
    ['/answer', '/next', '/check-answer', '/answer', '/next']);

  // A dropped response must not send a second POST or force a page reload.
  current = q1; fail = true;
  const before = calls.length;
  await submit(q1.nodes['#answer-form']);
  assert.deepEqual(calls.slice(before).map(call => call.url), ['/answer', '/practice']);
  assert.match(q1.nodes['#practice-status'].textContent, /Connexion/);
  assert.ok(q1.nodes['#answer-form'].controls.every(control => !control.disabled));
  return 'Practice checks passed: answer, next word, live validation, focus, results, and offline recovery without navigation.';
};
if (require.main === module) module.exports().then(console.log).catch(error => { console.error(error); process.exitCode = 1; });
