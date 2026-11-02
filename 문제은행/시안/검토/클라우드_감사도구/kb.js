const {open}=require('./h.js');const fs=require('fs');
const SHOT='/home/claude/english-question-bank/문제은행/시안/검토/스크린샷/클라우드/';
const info=p=>p.evaluate(()=>{const e=document.activeElement;if(!e||e===document.body)return {s:'BODY'};const r=e.getBoundingClientRect(),cs=getComputedStyle(e);
 const sel=(e.id?'#'+e.id:e.tagName.toLowerCase()+(Object.keys(e.dataset)[0]?'[data-'+Object.keys(e.dataset)[0]+']':''));
 return {s:sel,n:(e.getAttribute('aria-label')||e.innerText||e.placeholder||'').replace(/\s+/g,' ').slice(0,24),
  inDrawer:!!e.closest('#drawer'),drawerOpen:!document.getElementById('drawer').classList.contains('translate-x-full'),inPrint:!!e.closest('#printModal'),
  onscreen:r.right>0&&r.left<innerWidth&&r.bottom>0&&r.top<innerHeight&&r.width>0,
  ring:(cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>0)?('outline '+cs.outlineWidth+' '+cs.outlineColor):(cs.boxShadow!=='none'?'shadow':'NONE')}});
async function walk(p,n,label){const L=[];for(let i=0;i<n;i++){await p.keyboard.press('Tab');L.push(await info(p))}return L}
const fmt=L=>L.map((x,i)=>`${i+1}.${x.s}「${x.n||''}」${x.ring==='NONE'?' [표시없음]':''}${x.onscreen===false?' [화면밖]':''}${x.inDrawer&&!x.drawerOpen?' [닫힌서랍]':''}`).join('\n');
(async()=>{const R={};
 // 1. home tab walk
 let {b,p}=await open(1440);await p.keyboard.press('Tab');
 R.home=await walk(p,30);console.log('== HOME TAB\n'+fmt(R.home));
 // 2. find tab walk
 await p.evaluate(()=>{S.view='find';render()});await p.evaluate(()=>document.activeElement.blur());
 R.find=await walk(p,70);console.log('== FIND TAB\n'+fmt(R.find));
 // focus visibility screenshot on a table row button
 await p.focus('[data-open]');await p.screenshot({path:SHOT+'kb_focus_detail_1440.png'});
 // 3. drawer keyboard
 await p.focus('[data-open] >> nth=1');await p.keyboard.press('Enter');await p.waitForTimeout(500);
 const after=await info(p);console.log('== DRAWER open via Enter → focus',JSON.stringify(after));
 const D=await walk(p,25);console.log('== DRAWER TAB\n'+fmt(D));
 const left=D.filter(x=>!x.inDrawer).length;console.log('drawer: tabs leaving drawer',left,'/25');
 await p.focus('#dt-q');await p.keyboard.press('ArrowRight');await p.waitForTimeout(200);
 console.log('arrow on tab →',JSON.stringify(await info(p)),await p.evaluate(()=>document.getElementById('dt-sol').getAttribute('aria-selected')));
 console.log('tabs tabindex',await p.evaluate(()=>[...document.querySelectorAll('[role=tab]')].map(t=>t.id+':'+t.getAttribute('tabindex')+':'+t.getAttribute('aria-selected'))));
 console.log('dialog attrs',await p.evaluate(()=>{const d=document.getElementById('drawer');return {role:d.getAttribute('role'),modal:d.getAttribute('aria-modal'),lb:d.getAttribute('aria-labelledby'),label:d.getAttribute('aria-label')}}));
 await p.screenshot({path:SHOT+'kb_drawer_focus_1440.png'});
 await p.keyboard.press('Escape');await p.waitForTimeout(400);console.log('Esc → focus',JSON.stringify(await info(p)));
 // closed drawer reachable?
 console.log('closed drawer focusables',await p.evaluate(()=>{const d=document.getElementById('drawer');return [...d.querySelectorAll('button,a,input,select,[tabindex]')].filter(e=>e.tabIndex>=0).length+' inert='+d.inert+' aria-hidden='+d.getAttribute('aria-hidden')+' vis='+getComputedStyle(d).visibility}));
 // 4. picker
 await p.focus('[data-so]');await p.keyboard.press('Enter');await p.waitForTimeout(300);
 console.log('== PICKER after Enter',JSON.stringify(await info(p)),await p.evaluate(()=>document.querySelector('[data-so]').getAttribute('aria-expanded')));
 const P=await walk(p,14);console.log(fmt(P));
 await p.keyboard.press('Escape');await p.waitForTimeout(200);console.log('picker Esc: expanded=',await p.evaluate(()=>document.querySelector('[data-so]').getAttribute('aria-expanded')),JSON.stringify(await info(p)));
 // 5. print modal via keyboard
 await p.click('#addAllBtn');await p.focus('#printBtn');await p.keyboard.press('Enter');await p.waitForTimeout(900);
 console.log('== PRINT open → focus',JSON.stringify(await info(p)));
 console.log('print dialog attrs',await p.evaluate(()=>{const d=document.getElementById('printModal');const inner=d.querySelector('[role=dialog]')||d;return {role:inner.getAttribute('role'),modal:inner.getAttribute('aria-modal'),lb:inner.getAttribute('aria-labelledby')}}));
 const PM=await walk(p,45);console.log(fmt(PM));console.log('print: tabs leaving modal',PM.filter(x=>!x.inPrint).length,'/45');
 await p.screenshot({path:SHOT+'kb_print_focus_1440.png'});
 await p.keyboard.press('Escape');await p.waitForTimeout(300);console.log('print Esc → focus',JSON.stringify(await info(p)));
 // 6. sets
 await p.evaluate(()=>{saveSet();S.view='sets';render()});await p.waitForTimeout(300);await p.evaluate(()=>document.activeElement.blur());
 p.on('dialog',d=>d.accept());const SE=await walk(p,20);console.log('== SETS TAB\n'+fmt(SE));
 // view change focus
 await p.focus('a[data-view=find]');await p.keyboard.press('Enter');await p.waitForTimeout(300);console.log('nav Enter → focus',JSON.stringify(await info(p)));
 // skip link / landmarks
 console.log('landmarks',await p.evaluate(()=>({main:document.querySelectorAll('main,[role=main]').length,skip:[...document.querySelectorAll('a[href^="#"]')].slice(0,3).map(a=>a.getAttribute('href')+':'+a.innerText.slice(0,10)),h1:[...document.querySelectorAll('h1')].map(h=>h.innerText), lang:document.documentElement.lang, enLang:document.querySelectorAll('[lang=en]').length, live:[...document.querySelectorAll('[aria-live],[role=status],[role=alert]')].map(e=>(e.id||e.className).toString().slice(0,20)+':'+(e.getAttribute('aria-live')||e.getAttribute('role')))})));
 console.log('randBtn',await p.evaluate(()=>{const b=document.getElementById('randBtn');return b.outerHTML.slice(0,300)+' | visible-rand: '+[...document.querySelectorAll('button')].filter(x=>/무작위/.test(x.innerText)).map(x=>x.outerHTML.slice(0,160)).join(' || ')}));
 console.log('nav-off',await p.evaluate(()=>document.querySelector('.nav-off').outerHTML.slice(0,200)));
 console.log('errs',p.errs.filter(e=>!e.includes('FILE_NOT')));
 await b.close();
 // 7. 390 drawer keyboard + reachability of detail button
 ({b,p}=await open(390,844,{touch:true}));await p.evaluate(()=>{S.view='find';render()});await p.waitForTimeout(300);
 console.log('390 findView overflow',await p.evaluate(()=>{const f=document.getElementById('findView');const cs=getComputedStyle(f);let n=document.querySelector('[data-open]');const chain=[];while(n&&n!==document.body){const c=getComputedStyle(n);if(c.overflowX!=='visible')chain.push((n.id||n.tagName)+':'+c.overflowX);n=n.parentElement}return chain.join(' > ')}));
 await b.close();
})();
