// 執行前先於 5055 啟動 Flask；PLAYWRIGHT_MODULE 可指定外部 Playwright 套件路徑。
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:5055');
    const field = name => page.locator(`[name="${name}"]`);
    await field('building').selectOption('test_building');
    await field('classroom').fill('302');
    await field('equipment').selectOption('test_equipment');
    await field('description').selectOption('test_problem');
    await field('contact_name').fill('瀏覽器測試');
    await field('contact_email').fill('student@example.com');
    assert.equal(await page.locator('#ticket-form').evaluate(f => f.checkValidity()), true);
    for (const name of ['building', 'classroom', 'contact_name', 'contact_email']) {
      const old = await field(name).inputValue();
      if (name === 'building') await field(name).selectOption('');
      else await field(name).fill('');
      assert.equal(await page.locator('#ticket-form').evaluate(f => f.checkValidity()), false);
      if (name === 'building') await field(name).selectOption(old);
      else await field(name).fill(old);
    }
    for (const email of ['invalid', 'a@localhost', 'a@-example.com']) {
      await field('contact_email').fill(email);
      assert.equal(await field('contact_email').evaluate(f => f.checkValidity()), false);
    }
    await field('contact_email').fill('student+tag@example.com');
    for (const name of ['equipment', 'description']) {
      await field(name).selectOption('other');
      assert.equal(await field(`${name}_other`).isVisible(), true);
      assert.equal(await field(`${name}_other`).evaluate(f => f.required), true);
      assert.equal(await page.locator('#ticket-form').evaluate(f => f.checkValidity()), false);
      await field(`${name}_other`).fill('自訂測試');
      await field(name).selectOption(name === 'equipment' ? 'test_equipment' : 'test_problem');
      assert.equal(await field(`${name}_other`).isVisible(), false);
      assert.equal(await field(`${name}_other`).isDisabled(), true);
      const keys = await page.locator('#ticket-form').evaluate(f => [...new FormData(f).keys()]);
      assert.equal(keys.includes(`${name}_other`), false);
    }
    await field('urgency').selectOption('緊急');
    const requestPromise = page.waitForRequest(r => r.method() === 'POST' && r.url().endsWith('/api/tickets'));
    await page.getByRole('button', { name: '送出報修' }).click();
    const payload = (await requestPromise).postDataJSON();
    assert.equal('equipment_other' in payload, false);
    assert.equal('description_other' in payload, false);
    await page.waitForFunction(() => document.querySelector('#message').textContent.includes('報修已建立'));
    const ticketId = (await page.locator('#message').textContent()).match(/T-\d+/)[0];
    assert.equal(await field('building').inputValue(), '');
    assert.equal(await field('equipment_other').isDisabled(), true);
    // 再以兩個「其他」建立案件，確認保存與重設。
    await field('building').selectOption('test_building');
    await field('classroom').fill('303');
    await field('equipment').selectOption('other');
    await field('equipment_other').fill('自訂設備');
    await field('description').selectOption('other');
    await field('description_other').fill('自訂故障');
    await field('contact_name').fill('測試同學');
    await field('contact_email').fill('name@example.org');
    const responsePromise = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/tickets'));
    await page.getByRole('button', { name: '送出報修' }).click();
    assert.equal((await responsePromise).status(), 201);
    await page.waitForFunction(() => document.querySelector('[name="equipment"]').value === '');
    assert.equal(await field('description_other').isDisabled(), true);
    await page.goto('http://127.0.0.1:5055/admin');
    const row = page.locator('tbody tr').filter({ hasText: ticketId });
    await row.locator('select').selectOption('處理中');
    let patchCount = 0;
    page.on('request', r => { if (r.method() === 'PATCH') patchCount++; });
    await row.locator('input').fill('   ');
    await row.getByRole('button', { name: '儲存案件' }).click();
    assert.equal(patchCount, 0);
    assert.match(await page.locator('#message').textContent(), /必須填寫維修負責人/);
    await row.locator('input').fill('測試技師');
    await row.getByRole('button', { name: '儲存案件' }).click();
    await page.waitForFunction(() => document.querySelector('#message').textContent.includes('已更新'));
    assert.equal(await row.locator('select').inputValue(), '處理中');
    assert.equal(await row.locator('input').inputValue(), '測試技師');
    for (const status of ['已結案', '已派工', '待料中', '待審核']) {
      await row.locator('select').selectOption(status);
      if (status === '待審核') await row.locator('input').fill('');
      const saved = page.waitForResponse(r => r.request().method() === 'PATCH');
      await row.getByRole('button', { name: '儲存案件' }).click();
      assert.equal((await saved).status(), 200);
      await page.waitForFunction(({ id, status }) => {
        const row = [...document.querySelectorAll('tbody tr')].find(r => r.cells[0].textContent === id);
        return row.querySelector('select').value === status && !row.querySelector('button').disabled;
      }, { id: ticketId, status });
    }
    assert.equal(await row.locator('input').inputValue(), '');
    assert.equal(await page.getByRole('columnheader', { name: '聯絡方式' }).count(), 0);
    console.log('PASS: 必填、Email、其他切換、JSON 排除、建立、重設、後台更新');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
