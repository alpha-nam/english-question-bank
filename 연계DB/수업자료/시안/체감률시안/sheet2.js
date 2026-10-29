const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const pg = await b.newPage({viewport: {width: 1200, height: 800}});
  await pg.goto('file://' + path.join(__dirname, process.argv[2]));
  await pg.evaluate(() => document.fonts.ready);
  await pg.waitForTimeout(1500);
  await pg.screenshot({path: path.join(__dirname, process.argv[3]), fullPage: true});
  await b.close();
})();
