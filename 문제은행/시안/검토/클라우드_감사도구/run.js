const {open}=require('./h.js');const fs=require('fs');const {chromium}=require('playwright');
const SHOT='/home/claude/english-question-bank/문제은행/시안/검토/스크린샷/클라우드/';fs.mkdirSync(SHOT,{recursive:true});
const CHK=fs.readFileSync(__dirname+'/checks.js','utf8');
const W=[1440,1024,768,390];
const nav=async(p,v)=>{await p.evaluate(v=>{S.view=v;render()},v);await p.waitForTimeout(250)};
const SC={
 home:async p=>{},
 find_table:async p=>{await nav(p,'find')},
 picker:async p=>{await nav(p,'find');await p.locator('[data-so]').first().click();await p.waitForTimeout(250)},
 find_book:async p=>{await nav(p,'find');await p.locator('[data-src=book]').first().click();await p.waitForTimeout(250)},
 drawer_q:async p=>{await nav(p,'find');await p.evaluate(()=>openDrawer(document.querySelectorAll('[data-open]')[1].dataset.open));await p.waitForTimeout(500)},
 drawer_sol:async p=>{await nav(p,'find');await p.evaluate(()=>openDrawer(document.querySelectorAll('[data-open]')[1].dataset.open));await p.waitForTimeout(400);await p.click('#dt-sol');await p.waitForTimeout(250)},
 print:async p=>{await nav(p,'find');await p.click('#addAllBtn');await p.evaluate(()=>openPrint());await p.waitForTimeout(900)},
 sets:async p=>{await nav(p,'find');await p.click('#addAllBtn');await p.evaluate(()=>saveSet());await p.waitForTimeout(200);await p.waitForTimeout(3500);await nav(p,'sets')},
};
(async()=>{const browser=await chromium.launch();const out={};
const ONLY=process.argv[2];const prev=ONLY?require('./result.json'):{};Object.assign(out,prev);for(const [name,fn] of Object.entries(SC).filter(([n])=>!ONLY||n===ONLY))for(const w of W){
 const {ctx,p}=await open(w,w>=1024?900:(w>=768?1024:844),{browser,touch:w<=768});p.on('dialog',d=>d.accept('예시 문제지').catch(()=>{}));
 try{await fn(p)}catch(e){out[name+'_'+w]={error:String(e).slice(0,200)};await ctx.close();continue}
 await p.addScriptTag({content:CHK});const r=await p.evaluate(()=>__a11y());r.errs=p.errs.filter(e=>!e.includes('FILE_NOT_FOUND'));
 await p.screenshot({path:SHOT+`${name}_${w}.png`});out[name+'_'+w]=r;await ctx.close();}
if(!ONLY){
for(const w of [1440,390]){const {ctx,p}=await open(w,w>=1024?900:844,{browser,scheme:'dark',touch:w<768});await p.addScriptTag({content:CHK});const r=await p.evaluate(()=>({bg:getComputedStyle(document.body).backgroundColor,color:getComputedStyle(document.body).color,cs:matchMedia('(prefers-color-scheme: dark)').matches}));await p.screenshot({path:SHOT+`dark_home_${w}.png`});out['dark_'+w]=r;await ctx.close()}}
fs.writeFileSync(__dirname+'/result.json',JSON.stringify(out,null,1));await browser.close();
for(const [k,r] of Object.entries(out)){if(r.error){console.log(k,'ERR',r.error);continue}if(r.bg){console.log(k,JSON.stringify(r));continue}
 console.log(k.padEnd(16),'대비실패',r.contrast.length,'15px미만',r.smallN,'(13미만',r.small13+')','작은터치',r.targetsN,'이름없음',r.noname.length,'가로스크롤',r.hscroll,'잘림',r.clipped.length,'오류',r.errs.length)}
})();
