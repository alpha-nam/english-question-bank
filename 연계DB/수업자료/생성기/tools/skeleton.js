// 덱 HTML 은 Artifact 에 올리는 모양(문서 형식 선언·head·body 가 없는 조각)이다. 크롬이 이 조각을 파일로 그냥 열면 괴상 모드(quirks)로 읽어서,
// Artifact 가 틀을 씌워 보여 주는 실제 화면(표준 모드)과 칸 배치가 다르다(2026-10-23 발견: 같은 덱에서 칸 441개의 자리가 다르고
// 25번 비교 장 머리글 여유가 5~9px 달랐다). 그래서 검사·PDF·화면 시험 도구는 모두 이 모듈로 Artifact 와 같은 틀을 씌워서 연다.
// 틀 글은 template/skeleton_head.html, skeleton_tail.html 한 곳에 있고 build.py 의 standalone() 도 같은 글을 쓴다.
//   const sk = require('./skeleton');  const p = sk.prepared(파일);  await pg.goto('file://' + p.file);  ...  p.done();
const fs = require('fs');
const os = require('os');
const path = require('path');

const TPL = path.join(__dirname, '..', 'template');
const HEAD = fs.readFileSync(path.join(TPL, 'skeleton_head.html'), 'utf8');
const TAIL = fs.readFileSync(path.join(TPL, 'skeleton_tail.html'), 'utf8');
const hasDoctype = html => /^\s*<!doctype/i.test(html);

function wrap(html) { return hasDoctype(html) ? html : HEAD + html + TAIL; }

// 파일에 틀을 씌운 임시 파일을 만들어 그 경로를 돌려준다. 이미 문서 형식 선언이 있으면(독립 파일) 원래 경로 그대로.
function prepared(file) {
  const abs = path.resolve(file);
  const html = fs.readFileSync(abs, 'utf8');
  if (hasDoctype(html)) return {file: abs, wrapped: false, done() {}};
  const tmp = path.join(os.tmpdir(), 'skel_' + process.pid + '_' + Math.random().toString(36).slice(2) + '.html');
  fs.writeFileSync(tmp, wrap(html));
  return {file: tmp, wrapped: true, done() { try { fs.unlinkSync(tmp); } catch (e) { /* 이미 없음 */ } }};
}

module.exports = {wrap, prepared, hasDoctype};
