/* 첫 화면의 회차 탭: 눌러서 바꾸고, 화살표·Home·End 로 옮긴다(탭을 하나만 Tab 키로 거치고 나머지는 화살표로).
   주소 끝에 #2026.09 처럼 회차 이름(탭의 data-r)을 붙이면 그 회차가 열린다. 처음 열린 탭(가장 최근 회차)은 만들 때 이미 정해 둔다 */
(function(){var T=[].slice.call(document.querySelectorAll('.tabs [role=tab]'));
  function id(t){return t.getAttribute('data-r')}
  function show(r,move){T.forEach(function(t){var on=id(t)===r;
    t.setAttribute('aria-selected',on?'true':'false');t.tabIndex=on?0:-1;
    document.getElementById('panel-'+id(t)).hidden=!on;
    if(on&&move)t.focus()})}
  function pick(r,move){show(r,move);try{history.replaceState(null,'','#'+r)}catch(e){}}
  T.forEach(function(t,i){
    t.addEventListener('click',function(){pick(id(t))});
    t.addEventListener('keydown',function(e){
      var k=e.key,j=k==='ArrowRight'?i+1:k==='ArrowLeft'?i-1:k==='Home'?0:k==='End'?T.length-1:null;
      if(j===null)return;
      e.preventDefault();pick(id(T[(j+T.length)%T.length]),true)})});
  function fromHash(){var h='';try{h=decodeURIComponent((location.hash||'').slice(1))}catch(e){}
    if(T.some(function(t){return id(t)===h}))show(h)}
  window.addEventListener('hashchange',fromHash);fromHash()})();
