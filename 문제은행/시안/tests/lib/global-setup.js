// 시험 전에 한 번: 예시 화면을 다시 만들고(가짜 지문만), 로컬 Tailwind CSS를 만든다.
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const v = require('./vendor');

module.exports = async () => {
  if (process.env.QB_SKIP_BUILD !== '1') {
    const py = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
    execFileSync(py, ['build.py', '--예시'], { cwd: v.SIAN, stdio: 'inherit' });
  }
  if (!fs.existsSync(v.PAGE)) throw new Error('예시_화면시안.html 이 없습니다: ' + v.PAGE);
  if (!v.ONLINE) v.buildTailwind();
};
