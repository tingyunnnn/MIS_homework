# 校園設備報修系統

這是一個適合 MIS 課堂使用的最小前後端範例。學生透過網頁表單建立報修單，Flask 後端接收 JSON 資料、產生案件編號，再將結果回傳網頁。

## 系統需求

- Windows 10/11
- Python 3.13.x
- 瀏覽器（Edge、Chrome 皆可）

## 第一次啟動

在此專案資料夾開啟 PowerShell，依序執行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

看到下列訊息後，以瀏覽器開啟 <http://127.0.0.1:5000>：

```text
Running on http://127.0.0.1:5000
```

按 `Ctrl + C` 可停止伺服器。

管理後台位址為 <http://127.0.0.1:5000/admin>。可在此查看案件並更新狀態。

## 第二次以後啟動

```powershell
.\.venv\Scripts\python.exe app.py
```

## 觀察重點

1. 在 `templates/index.html` 找到表單欄位。
2. 在 `static/app.js` 找到 `fetch("/api/tickets")`：前端在這裡呼叫後端 API。
3. 在 `app.py` 找到 `@app.post("/api/tickets")`：Python 在這裡接收、驗證並回傳資料。
4. 在 `templates/admin.html` 與 `static/admin.js` 看管理員如何透過 `PATCH /api/tickets/<案件編號>` 更新狀態。

## 注意事項

本範例把案件資料存在 Python 的記憶體中，停止或重啟程式後，資料會清空。

## 第一階段：前台表單

大樓、設備及問題選項集中於 `app.py` 的 `FORM_OPTIONS`。目前帶有 `test_` 的值及標示「測試／待確認」的文字僅供課堂測試，並非正式校園資料。取得正式清單後在此集中替換，HTML 選項與後端驗證會使用相同設定。設備與問題清單須保留 `("other", "其他")`。

建立案件仍使用 `POST /api/tickets`，JSON 範例：

```json
{
  "building": "test_building",
  "classroom": "302",
  "equipment": "other",
  "equipment_other": "自訂設備",
  "description": "other",
  "description_other": "無法啟動",
  "contact_name": "測試同學",
  "contact_email": "student@example.com",
  "urgency": "一般"
}
```

選擇一般設備／問題時，自訂欄位隱藏、停用且清空，不會包含在表單 JSON；後端也忽略不適用的自訂內容。選擇 `other` 時，自訂內容必填。電子郵件使用 HTML `type="email"`、共享格式規則與後端驗證，接受一般 email 及子網域，不限制學校網域；格式驗證不代表信箱確實存在。

有效資料回傳 HTTP 201；無效資料回傳 HTTP 400 及中文 `message`。回傳案件的 `equipment`、`description` 是供表格顯示的文字，原選項值另存於 `equipment_type`、`description_type`，`location` 是大樓標籤與詳細位置的組合。

由於後台尚無登入保護，依第一階段需求，前後台清單均暫不顯示報修人姓名及 Email。聯絡資料仍保存在後端記憶體，所有案件 API 回應均排除聯絡欄位。

## 第二階段：後台狀態與人員指派

新案件預設為「待審核」，維修負責人 `assignee` 預設空字串。管理員在 `/admin` 選擇狀態、自由輸入維修負責人姓名，再按「儲存案件」一次保存兩個欄位。五種狀態為「待審核、已派工、處理中、待料中、已結案」，可自由切換，不限制順序。選項集中於 `app.py` 的 `STATUSES`，後台使用同一份設定。

「待審核」可不填負責人；其他四種狀態必須填寫，純空白不算有效姓名。前端及後端皆檢查此規則，儲存失敗會顯示中文訊息，保留輸入且不改動案件資料。

既有 `PATCH /api/tickets/<案件編號>` 路由保留，更新範例：

```json
{"status": "已派工", "assignee": "王技師"}
```

成功回傳 HTTP 200、`message` 及最新 `ticket`；格式、狀態或負責人驗證失敗回傳 HTTP 400，不會只更新其中一個欄位；合法更新但案件不存在回傳 HTTP 404。省略 `assignee` 時保留原負責人，明確傳空字串可在「待審核」時清除指派。`status` 仍須提供，舊值「待處理、已完成」不再接受。

案件回應新增 `assignee`，報修人的 `contact_name`、`contact_email` 仍不公開。現有共用清單 API 可讀取維修負責人，前台表格不顯示此欄。系統仍採記憶體儲存，沒有新增資料庫或 Email 通知；實際部署前仍需補登入與權限控制。

## 測試

Flask test client 模擬 API 請求，不必啟動伺服器，也不需要額外測試套件：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`tests/browser.cjs` 使用 Playwright 與本機 Edge 驗證前端。先以有效的 Python 環境啟動 Flask 於 5055，再於具備 Playwright 的 Node.js 環境執行：

```powershell
.\.venv\Scripts\python.exe -m flask --app app run --port 5055
# 另一個終端機；如果套件不在一般搜尋路徑，可設定 PLAYWRIGHT_MODULE 指向套件。
node tests/browser.cjs
```

瀏覽器測試會建立測試案件及更新測試案件狀態，請使用獨立測試伺服器。手機排版及實際校園選項仍需人工確認。
