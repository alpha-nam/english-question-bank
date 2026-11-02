const {chromium}=require('playwright');const fs=require('fs');const E=__dirname;
const TW=fs.readFileSync(E+'/tw.css','utf8');
const QR=fs.readFileSync(E+'/node_modules/qrcode-generator/qrcode.js','utf8');
const PD=E+'/node_modules/pretendard/dist/web/variable/';
const FILE='/home/claude/english-question-bank/문제은행/시안/예시_화면시안.html';
async function open(w,h,opts={}){const b=opts.browser||await chromium.launch();const ctx=await b.newContext({viewport:{width:w,height:h||900},colorScheme:opts.scheme||'light',hasTouch:!!opts.touch,isMobile:!!opts.touch});
 await ctx.route('**/*',async r=>{const u=r.request().url();
  if(u.startsWith('https://cdn.tailwindcss.com'))return r.fulfill({contentType:'application/javascript',body:'document.head.insertAdjacentHTML("afterbegin",'+JSON.stringify('<style id="twlocal">'+TW+'</style>')+')'});
  if(u.includes('qrcode'))return r.fulfill({contentType:'application/javascript',body:QR});
  if(u.includes('pretendard')){if(u.endsWith('.css'))return r.fulfill({contentType:'text/css',body:fs.readFileSync(PD+'pretendardvariable-dynamic-subset.css','utf8').replace(/url\(\.\.?\/?/g,'url(https://pd.local/')});}
  if(u.startsWith('https://pd.local/')){const p=PD+u.slice(17);if(fs.existsSync(p))return r.fulfill({body:fs.readFileSync(p),contentType:'font/woff2'});return r.fulfill({status:404,body:''})}
  if(u.startsWith('file:')||u.includes('fonts.g'))return r.continue();
  return r.continue().catch(()=>{});});
 const p=await ctx.newPage();p.errs=[];p.on('pageerror',e=>p.errs.push(String(e)));p.on('console',m=>{if(m.type()==='error')p.errs.push(m.text())});
 await p.goto('file://'+FILE);await p.waitForTimeout(800);return {b,ctx,p};}
module.exports={open};
