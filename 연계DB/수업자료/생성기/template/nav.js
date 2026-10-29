/* 위 목차 줄: (1) 줄이 폰에서 두세 줄로 접혀도 이동한 장의 위쪽이 가려지지 않게, 목차 줄의 높이를 재어 장 위 여백(--navh, nav.css)에 쓴다.
   (2) 이전 문항·다음 문항 단추(data-go): 지금 보는 문항을 찾아 앞뒤 문항의 첫 장으로 옮긴다(맨 앞 문항에서 이전은 연계 지도, 지도가 없으면 맨 앞 문항) */
(function(){var n=document.querySelector('nav');
  function set(){if(n)document.documentElement.style.setProperty('--navh',n.offsetHeight+'px')}
  set();window.addEventListener('resize',set);window.addEventListener('load',set);
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(set)})();
(function(){var Q=[].slice.call(document.querySelectorAll('.slide[id^="q"]'));
  function cur(){var y=window.innerHeight*.35,b=-1;Q.forEach(function(s,i){if(s.getBoundingClientRect().top<y)b=i});return b}
  [].slice.call(document.querySelectorAll('nav [data-go]')).forEach(function(a){
    a.addEventListener('click',function(e){
      e.preventDefault();
      var i=cur()+(a.getAttribute('data-go')==='next'?1:-1);
      var t=i<0?(document.getElementById('map')||Q[0]):Q[i];
      if(t)t.scrollIntoView({behavior:'smooth',block:'start'})})})})();
