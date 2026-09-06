import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(process.env.PLAYWRIGHT_PACKAGE_ROOT);
const { chromium } = require('playwright');
const browser = await chromium.launch({ headless: true, executablePath: process.env.QA_BROWSER_PATH });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  page.setDefaultTimeout(12_000);
  page.on('pageerror', error => console.log('PAGE ERROR', error.message));
  const posts = [];
  let gets = 0;
  let mode = 'disconnect';
  const facts = { base_hexagram: { king_wen_number: 59, name: '风水涣' } };
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    let status = 200;
    let payload = { status: 'PASS', intake_id: 'intake-' + 'a'.repeat(32) };
    if (url.pathname === '/api/direct-reading/v2') {
      if (route.request().method() === 'POST') {
        posts.push(route.request().postData());
        status = posts.length === 1 ? 503 : 202;
        payload = posts.length === 1 ? { error_code: 'ENGINE_WAKING', not_submitted: true } :
          { status: 'RUNNING', stage: 'CAST_READY', chart_facts: facts };
      } else {
        gets++;
        status = mode === 'disconnect' ? 503 : 202;
        payload = mode === 'disconnect' ? { error: '连接暂时中断', retry_after_seconds: 1 } :
          { status: 'RUNNING', stage: 'MODEL_STREAMING', chart_facts: facts };
      }
    }
    await route.fulfill({ status, contentType: 'application/json', headers: { 'Retry-After': '1' }, body: JSON.stringify(payload) });
  });
  await page.goto(`${process.env.QA_ORIGIN || 'http://localhost:3006'}/?continue-question=1`);
  await page.locator('#primary-question').fill('我应该集中资源推进这个测试项目吗？');
  await page.getByRole('button', { name: '问题已经写好 继续' }).click();
  for (const [index, value] of ['3', '77', '46'].entries()) await page.getByRole('spinbutton', { name: `第${index + 1}个数字` }).fill(value);
  await page.getByRole('button', { name: '三个数已经取好 开始成卦' }).click();
  await page.getByRole('button', { name: '继续获取解卦' }).waitFor({ state: 'visible' });
  assert.equal(posts.length, 2);
  assert.equal(posts[0], posts[1]);
  assert.equal(gets, 4);
  console.log('cold wake + persistent interruption:', await page.locator('body').innerText());
  mode = 'running';
  await page.getByRole('button', { name: '继续获取解卦' }).click();
  try { await page.getByText('正在撰写详细解卦，完成后即可查看。', { exact: true }).waitFor({ state: 'visible' }); }
  catch (error) { console.log('RESUME', { posts: posts.length, gets, text: await page.locator('body').innerText() }); throw error; }
  assert.equal(posts.length, 2, 'Resume must not submit again');
  for (const width of [320, 390, 430]) {
    await page.setViewportSize({ width, height: 844 });
    const box = await page.locator('.direct-high-pending-message').boundingBox();
    assert.ok(box && box.x >= 0 && box.x + box.width <= width + 1 && box.y + box.height <= 844, JSON.stringify(box));
  }
  await page.screenshot({ path: 'work/hotfix-p7-mobile.png' });
  console.log('PASS: cold wake, original-task recovery, no duplicate model dispatch, visible progress at 320/390/430px');
} finally { await browser.close(); }
