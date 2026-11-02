// injected into page: returns detailed findings with selectors
window.__a11y=function(mode){
 const W=innerWidth, minT = W>=1024?40:44;
 const sel=e=>{if(!e||e.nodeType!==1)return '';if(e.id)return '#'+e.id;let s=e.tagName.toLowerCase();for(const k of Object.keys(e.dataset||{}))if(k!=='i'){s+=`[data-${k.replace(/[A-Z]/g,m=>'-'+m.toLowerCase())}]`;break}
   const c=(e.getAttribute('class')||'').split(/\s+/).filter(x=>x&&!x.includes(':')&&!x.includes('[')&&!x.includes('/')).slice(0,2);if(c.length)s+='.'+c.join('.');
   const p=e.parentElement;const pid=p&&p.closest('[id]');return (pid&&pid!==e?'#'+pid.id+' ':'')+s};
 function parse(c){const m=c.match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat);return{r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}}
 function over(t,b){const a=t.a+b.a*(1-t.a);if(!a)return{r:0,g:0,b:0,a:0};return{r:(t.r*t.a+b.r*b.a*(1-t.a))/a,g:(t.g*t.a+b.g*b.a*(1-t.a))/a,b:(t.b*t.a+b.b*b.a*(1-t.a))/a,a}}
 function lum(c){const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b)}
 const ratio=(a,b)=>{const l1=lum(a),l2=lum(b);return(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05)};
 function bgOf(el){let L=[],n=el;while(n&&n.nodeType===1){const c=parse(getComputedStyle(n).backgroundColor);if(c&&c.a>0)L.push(c);if(c&&c.a>=1)break;n=n.parentElement}let acc={r:255,g:255,b:255,a:1};for(let i=L.length-1;i>=0;i--)acc=over(L[i],acc);return acc}
 const vis=e=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'&&r.bottom>0&&r.right>0&&r.left<W&&r.top<innerHeight&&!e.closest('[aria-hidden=true],.hidden')};
 const own=e=>{let t='';for(const n of e.childNodes)if(n.nodeType===3)t+=n.nodeValue;return t.replace(/\s+/g,' ').trim()};
 const R={w:W,minT,contrast:[],small:[],small13:0,textN:0,targets:[],noname:[],hscroll:document.documentElement.scrollWidth>W+1,wide:[],clipped:[]};
 const seenC=new Set();
 for(const el of document.querySelectorAll('body *')){
  if(['SCRIPT','STYLE','svg','path'].includes(el.tagName)||!vis(el))continue;
  const t=own(el),cs=getComputedStyle(el);
  if(t&&!el.closest('.xp,.a4,#pvArea .page')){ // 인쇄 미리보기 종이 안은 제외(종이 축소 표시)
   const fg=parse(cs.color);if(fg){const bg=bgOf(el),f=over(fg,bg),r=ratio(f,bg),fs=parseFloat(cs.fontSize),bold=parseInt(cs.fontWeight)>=700;const need=(fs>=24||(fs>=18.66&&bold))?3:4.5;
    R.textN++;if(r<need){const k=sel(el)+'|'+r.toFixed(2);if(!seenC.has(k)){seenC.add(k);R.contrast.push({s:sel(el),t:t.slice(0,20),r:+r.toFixed(2),need,fs,fg:cs.color,bg:`rgb(${bg.r|0},${bg.g|0},${bg.b|0})`})}}
    if(fs<15){R.small.push({s:sel(el),t:t.slice(0,16),fs});if(fs<13)R.small13++}}
  }
  const tag=el.tagName,role=el.getAttribute('role');
  const inter=['BUTTON','A','SELECT','INPUT','TEXTAREA','SUMMARY'].includes(tag)||['button','tab','link','checkbox','radio'].includes(role);
  if(inter&&!(tag==='INPUT'&&el.type==='hidden')){
   const r=el.getBoundingClientRect();let w=r.width,h=r.height;
   // 체크박스·라디오는 label 영역까지 포함
   if(tag==='INPUT'&&(el.type==='checkbox'||el.type==='radio')){const lb=el.closest('label')||(el.id&&document.querySelector(`label[for="${el.id}"]`));if(lb){const q=lb.getBoundingClientRect();w=Math.max(w,q.width);h=Math.max(h,q.height)}}
   const inline = tag==='A' && cs.display==='inline' && el.closest('p');
   if(Math.min(w,h)<minT&&!inline)R.targets.push({s:sel(el),t:(el.getAttribute('aria-label')||el.innerText||el.value||'').replace(/\s+/g,' ').slice(0,18),w:Math.round(w),h:Math.round(h)});
   let name=(el.getAttribute('aria-label')||'').trim();
   if(!name&&el.getAttribute('aria-labelledby'))name=el.getAttribute('aria-labelledby').split(' ').map(i=>(document.getElementById(i)||{}).textContent||'').join(' ').trim();
   if(!name)name=(el.innerText||'').trim()||el.getAttribute('title')||'';
   if(!name&&tag==='INPUT'){name=(el.labels&&[...el.labels].map(l=>l.innerText).join(' ').trim())||el.placeholder||''}
   if(!name){const img=el.querySelector('img[alt]');if(img)name=img.alt}
   if(!name&&tag==='SELECT')name=(el.labels&&[...el.labels].map(l=>l.innerText).join(' ').trim())||'';
   if(!name)R.noname.push({s:sel(el),html:el.outerHTML.slice(0,120)});
  }
  if(R.hscroll){const r=el.getBoundingClientRect();if(r.right>W+1&&R.wide.length<6&&!el.closest('#drawer.translate-x-full'))R.wide.push({s:sel(el),right:Math.round(r.right)})}
  if(el.scrollWidth>el.clientWidth+2&&cs.overflowX!=='auto'&&cs.overflowX!=='scroll'&&cs.overflowX!=='visible'&&cs.textOverflow!=='ellipsis'&&!el.classList.contains('sr-only')&&R.clipped.length<6)R.clipped.push({s:sel(el),sw:el.scrollWidth,cw:el.clientWidth});
 }
 R.smallN=R.small.length;R.small=R.small.slice(0,15);R.targetsN=R.targets.length;R.targets=R.targets.slice(0,15);
 return R;
};
