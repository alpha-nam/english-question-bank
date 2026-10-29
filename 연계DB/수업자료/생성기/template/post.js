/* 줄바꿈 규칙: 한 문장을 뜻 덩어리(|)로 나누어, 줄이 바뀔 때는 덩어리 사이에서만 바뀌게 한다.
   따옴표 안의 영어 구와 굵게 쓴 영어 구는 한 덩어리로 묶어 중간에서 끊기지 않게 한다 */
document.querySelectorAll('.row li,.diff div').forEach(function(el){
  var h=el.innerHTML;
  if(h.indexOf('|')>=0){
    var lead='',m=h.match(/^\s*<b>(?:<span class="ic [^>]*><\/span>)?[^<]*<\/b>/);
    if(m&&el.closest('.diff')){lead=m[0];h=h.slice(m[0].length)}
    h=lead+h.split('|').map(function(t){return '<span class="cl">'+t.trim()+'</span>'}).join(' ');
  }
  el.innerHTML=h.replace(/(“[^”<]*”)/g,'<span class="nw">$1</span>');
  el.querySelectorAll('b').forEach(function(b){if(/[A-Za-z]/.test(b.textContent))b.classList.add('nw')})});
/* 남는 공간 채우기: 문항 장(시험·교재 원문항)만 글자와 그림을 칸 높이에 맞게 키운다. 비교·분석 장은 글자 크기를 고정한다 */
function fit(){
  var wide=window.innerWidth>700;
  document.querySelectorAll('.slide .q:not(.twofig)').forEach(function(c){
    var kids=[].slice.call(c.children);
    kids.forEach(function(k){k.style.zoom=''});
    if(!wide)return;
    var best=1;
    if(c.scrollHeight>c.clientHeight+1){
      for(var d=.96;d>=.7;d-=.01){kids.forEach(function(k){k.style.zoom=d});best=d;if(c.scrollHeight<=c.clientHeight+1)break}
      kids.forEach(function(k){k.style.zoom=best});return}
    for(var z=1.02;z<=1.6;z+=.01){
      kids.forEach(function(k){k.style.zoom=z});
      if(c.scrollHeight>c.clientHeight+1||c.scrollWidth>c.clientWidth+1)break;
      best=z}
    best=Math.max(1,best-.015);kids.forEach(function(k){k.style.zoom=best})});
  /* 쉽게 보기 장: 글이 길어 카드가 아래 칸(같아요·달라요)과 겹치면 카드 글자와 그림을 조금씩 줄인다 */
  document.querySelectorAll('.slide .flow').forEach(function(f){
    f.style.setProperty('--es',1);if(!wide)return;
    function over(){return f.scrollHeight>f.clientHeight+1||[].some.call(f.querySelectorAll('.ecard'),function(c){return c.scrollHeight>c.clientHeight+1})}
    for(var r=1;r>=.6&&over();r-=.03)f.style.setProperty('--es',r.toFixed(2))});
  /* 교사 분석 장: 글자는 고정, 내용이 넘칠 때만 조금씩 줄인다 */
  document.querySelectorAll('.slide .rows').forEach(function(c){
    c.style.setProperty('--rs',1);if(!wide)return;
    for(var r=1;r>=.75&&c.scrollHeight>c.clientHeight+1;r-=.04)c.style.setProperty('--rs',r.toFixed(2))});
}
(document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve()).then(fit);
window.addEventListener('load',function(){fit();setTimeout(fit,400);setTimeout(fit,1500)});var _t;window.addEventListener('resize',function(){clearTimeout(_t);_t=setTimeout(fit,150)});
/* 방향키로 슬라이드 이동 */
(function(){var S=[].slice.call(document.querySelectorAll('.slide'));
  function cur(){var y=window.innerHeight*.35,b=0;S.forEach(function(s,i){if(s.getBoundingClientRect().top<y)b=i});return b}
  document.addEventListener('keydown',function(e){
    if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;
    var i=cur()+(e.key==='ArrowRight'?1:-1);if(i<0||i>=S.length)return;
    S[i].scrollIntoView({behavior:'smooth',block:'start'});e.preventDefault()});})();
