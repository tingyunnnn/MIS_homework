// 執行前先於 5055 啟動 Flask；PLAYWRIGHT_MODULE 可指定外部 Playwright 套件路徑。
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const expectedOptions = require('./expected_options.json');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:5055');
    assert.equal(await page.getByText('MIS 前後端範例', { exact: true }).count(), 0);
    const field = name => page.locator(`[name="${name}"]`);
    for (const [name, key] of [['building', 'buildings'], ['equipment', 'equipment'], ['description', 'description']]) {
      const options = await field(name).locator('option').evaluateAll(nodes => nodes
        .filter(n => n.value !== '').map(n => [n.value, n.textContent]));
      assert.deepEqual(options, expectedOptions[key]);
      assert.equal(new Set(options.map(([value]) => value)).size, options.length);
      assert.equal(await field(name).evaluate(select => select.required), true);
    }
    assert.equal(await page.getByText('待確認', { exact: false }).count(), 0);
    await field('building').selectOption('liberal_arts_la');
    await field('classroom').fill('302');
    await field('equipment').selectOption('projector');
    await field('description').selectOption('cannot_power_on');
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
      await field(name).selectOption(name === 'equipment' ? 'projector' : 'cannot_power_on');
      assert.equal(await field(`${name}_other`).isVisible(), false);
      assert.equal(await field(`${name}_other`).isDisabled(), true);
      assert.equal(await field(`${name}_other`).inputValue(), '');
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
    await page.waitForFunction(id => [...document.querySelectorAll('tbody tr')]
      .some(row => row.cells[0].textContent === id), ticketId);
    const publicRow = page.locator('tbody tr').filter({ hasText: ticketId });
    assert.match(await publicRow.textContent(), /文學院大樓 LA 302/);
    assert.match(await publicRow.textContent(), /投影機/);
    assert.match(await publicRow.textContent(), /無法開機/);
    assert.equal(await publicRow.locator('td').count(), await page.locator('thead th').count());
    assert.equal((await publicRow.textContent()).includes('student+tag@example.com'), false);
    // 再以兩個「其他」建立案件，確認保存與重設。
    await field('building').selectOption('liberal_arts_la');
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
    assert.equal(await page.getByText('MIS 前後端範例', { exact: true }).count(), 0);
    const row = page.locator('tbody tr').filter({ hasText: ticketId });
    assert.deepEqual(await row.locator('select option').allTextContents(),
      ['待審核', '已派工', '處理中', '等待零件', '已結案']);
    assert.match(await row.textContent(), /文學院大樓 LA 302／投影機/);
    assert.match(await row.textContent(), /瀏覽器測試/);
    assert.match(await row.textContent(), /student\+tag@example.com/);
    assert.equal(await row.locator('td').count(), await page.locator('thead th').count());
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
    for (const status of ['已結案', '已派工', '等待零件', '待審核']) {
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
    for (const width of [1440, 1024, 768, 375, 320]) {
      await page.setViewportSize({ width, height: 900 });
      const layout = await page.evaluate(() => {
        const wrap = document.querySelector('.table-wrap');
        const header = document.querySelector('.repair-header').getBoundingClientRect();
        const link = document.querySelector('.repair-header .admin-link').getBoundingClientRect();
        const button = document.querySelector('tbody button');
        return { overflow: document.documentElement.scrollWidth > innerWidth,
          scrollable: wrap.scrollWidth > wrap.clientWidth,
          rightAligned: Math.abs(header.right - link.right) < 1,
          buttonNoWrap: getComputedStyle(button).whiteSpace === 'nowrap',
          idNoWrap: getComputedStyle(document.querySelector('tbody td')).whiteSpace === 'nowrap' };
      });
      assert.equal(layout.overflow, false);
      assert.equal(layout.rightAligned, true);
      assert.equal(layout.buttonNoWrap, true);
      assert.equal(layout.idNoWrap, true);
      if (width < 1440) assert.equal(layout.scrollable, true);
      await row.getByRole('button', { name: '儲存案件' }).scrollIntoViewIfNeeded();
      const saved = page.waitForResponse(r => r.request().method() === 'PATCH');
      await row.getByRole('button', { name: '儲存案件' }).click();
      assert.equal((await saved).status(), 200);
      await page.waitForFunction(() => !document.querySelector('tbody button').disabled);
      assert.match(await row.textContent(), /student\+tag@example.com/);
    }
    console.log('PASS: 三組正式選單順序及唯一值、中文及表格、必填、Email、其他切換及清除、JSON 排除、建立、重設、五階段後台更新');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
