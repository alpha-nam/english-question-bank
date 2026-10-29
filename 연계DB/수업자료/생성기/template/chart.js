/* 막대그래프: 도표를 그림 파일이 아니라 데이터로 다시 그린다.
   H: 그림 높이, compact: 비교 장용 요약판(범례 이름만, 주석 생략). 원본의 제목·범례 설명·주석·축 유무를 그대로 옮긴다 */
function chart(id,cfg,H,compact){
  var svg=document.getElementById(id);if(!svg)return;
  var W=580;H=H||330;
  var titles=[].concat(cfg.title),tl=titles.length,tfs=tl>1?15.5:17,tp=tl>1?20:22;
  var axis=cfg.axis!==false,n=cfg.groups.length,s=cfg.series.length;
  var L=axis?52:22,R=axis?14:22,gw=(W-L-R)/n,bw=Math.min(36,gw/(s+.9));
  var fills=['var(--paper)','url(#h'+id+')','var(--ink)'];
  var o='<defs><pattern id="h'+id+'" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--paper)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink)" stroke-width="2"/></pattern></defs>';
  var y=8+tfs;
  titles.forEach(function(t,i){o+='<text class="u" x="'+W/2+'" y="'+(y+i*tp)+'" text-anchor="middle" font-size="'+tfs+'" font-weight="700">'+t+'</text>'});
  y+=(tl-1)*tp+16;
  var boxed=cfg.defs&&!compact,legBottom;
  if(boxed){
    var mx=0;cfg.defs.forEach(function(d){mx=Math.max(mx,d.length)});
    var bwid=Math.min(W-24,mx*6.1+44),bx=(W-bwid)/2,bh=cfg.defs.length*16+8;
    o+='<rect x="'+bx+'" y="'+y+'" width="'+bwid+'" height="'+bh+'" fill="none" stroke="var(--ink)" stroke-width="1"/>';
    cfg.defs.forEach(function(d,i){var ry=y+6+i*16;
      o+='<rect x="'+(bx+8)+'" y="'+ry+'" width="12" height="12" fill="'+fills[i]+'" stroke="var(--ink)"/><text x="'+(bx+26)+'" y="'+(ry+10.5)+'" font-size="12">'+d+'</text>'});
    legBottom=y+bh;
  }else{
    var tw=-20;cfg.series.forEach(function(se){tw+=20+se.length*7.1+20});
    var lx=(W-tw)/2;
    cfg.series.forEach(function(se,i){
      o+='<rect x="'+lx+'" y="'+(y)+'" width="13" height="13" fill="'+fills[i]+'" stroke="var(--ink)"/><text x="'+(lx+19)+'" y="'+(y+11)+'" font-size="13">'+se+'</text>';
      lx+=20+se.length*7.1+20});
    legBottom=y+14;
  }
  var nl=(!compact&&cfg.note)?cfg.note.lines.length:0;
  var top=legBottom+(axis?26:24),base=H-6-40-(nl?nl*15+6:0),ph=base-top,ymax=cfg.ymax||100;
  if(axis){
    [0,20,40,60,80,100].forEach(function(v){var yy=base-ph*v/ymax;
      o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yy+'" y2="'+yy+'" stroke="var(--line)" stroke-width="1"/><text x="'+(L-8)+'" y="'+(yy+4.5)+'" text-anchor="end" font-size="13" style="fill:var(--sub)">'+v+'</text>'});
    o+='<text class="u" x="'+(L-8)+'" y="'+(top-15)+'" text-anchor="end" font-size="12" style="fill:var(--sub)">(%)</text>';
  }
  cfg.groups.forEach(function(g,gi){
    var x0=L+gi*gw+(gw-bw*s)/2;
    g.v.forEach(function(v,si){
      var h=ph*v/ymax,x=x0+si*bw;
      if(cfg.hl&&cfg.hl[0]==gi&&cfg.hl[1]==si)o+='<rect x="'+(x-5)+'" y="'+(base-h-28)+'" width="'+(bw+5)+'" height="'+(h+32)+'" rx="4" fill="none" stroke="var(--ok)" stroke-width="2.5" stroke-dasharray="5 3"/>';
      o+='<rect x="'+x+'" y="'+(base-h)+'" width="'+(bw-3)+'" height="'+h+'" fill="'+fills[si]+'" stroke="var(--ink)" stroke-width="1"/><text x="'+(x+(bw-3)/2)+'" y="'+(base-h-6)+'" text-anchor="middle" font-size="13">'+v+'%</text>';
    });
    o+='<text x="'+(L+gi*gw+gw/2)+'" y="'+(base+20)+'" text-anchor="middle" font-size="14.5" font-weight="600">'+g.name+'</text><text x="'+(L+gi*gw+gw/2)+'" y="'+(base+38)+'" text-anchor="middle" font-size="12.5" style="fill:var(--sub)">'+g.sub+'</text>';
  });
  o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+base+'" y2="'+base+'" stroke="var(--ink)"/>';
  if(nl){cfg.note.lines.forEach(function(t,i){
    var yy=base+38+20+i*15;
    o+='<text x="'+(axis?L-8:L)+'" y="'+yy+'" font-size="12" style="fill:var(--sub)">'+(i==0&&cfg.note.head?'<tspan font-style="italic">'+cfg.note.head+'</tspan> ':'')+t+'</text>'})}
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.innerHTML=o;
}
