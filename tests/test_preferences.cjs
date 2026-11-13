const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/preferences.js'), 'utf8');
const settle = async () => { for (let i=0; i<20; i++) await Promise.resolve(); };

function setup({ delayed=false, storage=new Map(), account='7' }={}) {
  const handlers={}, windowEvents={}, timers=new Map(), calls=[];
  let clock=0, release, failure=false;
  const gate=delayed ? new Promise(resolve => { release=resolve; }) : Promise.resolve();
  const controls=[
    {name:'name',type:'text',value:'Alice'},
    {name:'sound',type:'checkbox',checked:true},
    {name:'strict',type:'checkbox',checked:false},
    {name:'theme',type:'radio',value:'normal',checked:true},
    {name:'theme',type:'radio',value:'full-dark',checked:false},
    {name:'voice',type:'select-one',value:'svetlana'},
    {name:'length',type:'select-one',value:'10'},
  ];
  const form={addEventListener:(event,fn)=>{handlers[event]=fn;},querySelectorAll:()=>controls};
  const status={textContent:'',dataset:{}}, retry={hidden:true,addEventListener:(event,fn)=>{handlers.retry=fn;}};
  const document={
    body:{dataset:{interfaceUrl:'/settings/interface',userId:account,sound:'1'}},
    documentElement:{dataset:{theme:'normal'}},
    getElementById:id=>({'settings-form':form,'settings-save-status':status,'settings-retry':retry}[id] || null),
    querySelector:selector=>selector==='meta[name="csrf-token"]'?{content:'csrf-fixture'}:null,
    querySelectorAll:()=>[],
  };
  const window={addEventListener:(event,fn)=>{windowEvents[event]=fn;}};
  vm.runInNewContext(source,{
    window,document,AbortController,URLSearchParams,
    localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},
    setTimeout:(fn,delay)=>{timers.set(++clock,{fn,delay});return clock;},clearTimeout:id=>timers.delete(id),
    fetch:async(url,options)=>{calls.push({url,options});await gate;return {ok:!failure,status:failure?503:200,json:async()=>({saved:true})};},
  });
  return {calls,status,retry,storage,document,controls,release,
    fail:value=>{failure=value;},
    online:()=>windowEvents.online(),
    change:(name,value)=>{
      const control=controls.find(item=>item.name===name && (item.type!=='radio'||item.value===value));
      if(control.type==='checkbox') control.checked=value;else control.value=value;
      if(control.type==='radio') control.checked=true;
      handlers[control.type==='text'?'input':'change']({target:control});
    },
    tick:async()=>{
      const next=[...timers.entries()].sort((a,b)=>a[1].delay-b[1].delay)[0];
      if(next){timers.delete(next[0]);next[1].fn();await settle();}
    },
  };
}

module.exports=async function run(){
  const direct=setup();
  direct.change('theme','full-dark');
  assert.equal(direct.document.documentElement.dataset.theme,'full-dark','theme applies before a request');
  direct.change('sound',false);
  assert.equal(direct.document.body.dataset.sound,'0','sound switches off immediately');
  await direct.tick();
  assert.equal(direct.calls.length,1,'rapid changes share one save');
  assert.equal(direct.calls[0].options.body.get('csrf'),'csrf-fixture');
  assert.equal(direct.calls[0].options.body.get('sound'),'0','unchecked toggles are explicitly saved');
  assert.equal(direct.calls[0].options.body.get('theme'),'full-dark');
  assert.equal(direct.status.dataset.state,'saved');
  assert.equal(direct.storage.size,0,'acknowledged changes leave the recovery queue');

  const overlapping=setup({delayed:true});
  overlapping.change('voice','dmitry');await overlapping.tick();
  overlapping.change('voice','browser');await overlapping.tick();
  assert.equal(overlapping.calls.length,1,'there is only one request in flight');
  overlapping.release();await settle();await overlapping.tick();
  assert.equal(overlapping.calls.length,2);
  assert.equal(overlapping.calls[1].options.body.get('voice'),'browser','a late response cannot discard a newer choice');
  assert.equal(overlapping.status.dataset.state,'saved');

  const offline=setup();offline.fail(true);
  offline.change('length','20');await offline.tick();
  assert.equal(offline.status.dataset.state,'error');
  assert.equal(offline.retry.hidden,false);
  assert.equal(JSON.parse(offline.storage.get('slovo:7:pending-preferences')).length,'20');
  offline.fail(false);offline.online();await settle();
  assert.equal(offline.status.dataset.state,'saved','connection recovery retries the unsaved preference');

  const stored=new Map([['slovo:7:pending-preferences',JSON.stringify({theme:'full-dark',sound:0,length:'15'})]]);
  const restored=setup({storage:stored});
  assert.equal(restored.document.documentElement.dataset.theme,'full-dark');
  assert.equal(restored.controls.find(item=>item.name==='length').value,'15','a pending change survives navigation');
  await settle();assert.equal(restored.calls.length,1);
  const isolated=setup({account:'8',storage:new Map([['slovo:7:pending-preferences','{"sound":0}']])});
  assert.equal(isolated.document.body.dataset.sound,'1','another account does not inherit pending settings');
  assert.equal(isolated.calls.length,0);
  return 'Automatic preferences: instant application, batching, serialized saves, offline recovery, account isolation.';
};
if(require.main===module)module.exports().then(console.log).catch(error=>{console.error(error);process.exitCode=1;});
