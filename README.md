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

大樓、設備及問題選項集中於 `app.py` 的 `FORM_OPTIONS`，HTML 選項與後端驗證使用同一份設定。value 為固定英文 ID，不依選項順序或單一建築物代碼產生；改顯示名稱時應保留 ID。共用 IL 代碼的樓層與電腦教室各有獨立 ID。設備與問題的「其他」固定使用 `other`。

### 正式地點（依顯示順序）

| value | 顯示名稱 |
|---|---|
| `liberal_arts_la` | 文學院大樓 LA |
| `fine_arts_fa` | 藝術大樓 FA |
| `science_east_sc` | 理學院及東綜合大樓 SC |
| `bioscience_bi` | 生科館 BI |
| `physics_ph` | 物理館 PH |
| `chemistry_ch` | 化學館 CH |
| `materials_ms` | 材料大樓 MS |
| `electrical_ec` | 電資大樓 EC |
| `mechanical_en` | 機電大樓 EN |
| `management_cm` | 管理學院 CM |
| `marine_engineering_me` | 海工館 ME |
| `marine_research_ma` | 海科研究大樓及實驗大樓 MA |
| `marine_resources_mb` | 海資館 MB |
| `social_sciences_ss` | 社會科學院 SS |
| `siwan_library_10f_sw` | 西灣學院 圖資10F SW |
| `siwan_general_ge` | 西灣學院 綜合大樓 GE |
| `library_3f_il` | 圖資3樓 IL |
| `library_9f_il` | 圖資9樓 IL |
| `library_3_to_8f` | 圖書館(3~8樓) |
| `international_ir` | 國際研究大樓 IR |
| `library_computer_b1_il_pc` | 圖資大樓 電腦教室B1 IL PC |

### 正式設備

| value | 顯示名稱 |
|---|---|
| `projector` | 投影機 |
| `computer` | 電腦 |
| `air_conditioner` | 冷氣 |
| `microphone` | 麥克風 |
| `network_equipment` | 網路設備 |
| `other` | 其他 |

### 正式問題描述

| value | 顯示名稱 |
|---|---|
| `cannot_power_on` | 無法開機 |
| `malfunction` | 無法正常運作 |
| `connection_issue` | 連線異常 |
| `damaged` | 設備損壞 |
| `other` | 其他 |

### 前台操作

選擇大樓，填寫必填的教室／詳細位置，再選擇設備及問題描述。選擇「其他」時填寫自訂內容；切換回一般選項會清除並停用自訂欄位。填寫姓名、電子郵件，選擇一般／急件／緊急後按「送出報修」。成功會顯示案件編號、重設表單並更新清單。前台清單不顯示姓名與 Email，公開案件 API 也不回傳聯絡資訊；後台透過另外的無保護 API 顯示聯絡資料。

建立案件仍使用 `POST /api/tickets`，JSON 範例：

```json
{
  "building": "liberal_arts_la",
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

公開 `GET /api/tickets`、建立案件及 PATCH 回應均排除報修人姓名與 Email。後台使用新增的 `GET /api/admin/tickets`，回傳案件陣列，包含 `contact_name` 與 `contact_email`。此 API **尚無登入或存取保護**，知道網址的人即可讀取，不是安全或受限的管理員專用介面。

專案僅適合使用虛構資料進行本機課堂展示，請勿輸入真實個資或公開部署。登入與權限管理列為未來擴充項目，本次不實作。後台在表格中顯示姓名與電子郵件，窄螢幕可在案件表格水平捲動，查看狀態、負責人與儲存按鈕。

## 第二階段：後台狀態與人員指派

新案件預設為「待審核」，維修負責人 `assignee` 預設空字串。管理員在 `/admin` 選擇狀態、自由輸入維修負責人姓名，再按「儲存案件」一次保存兩個欄位。五種狀態為「待審核、已派工、處理中、等待零件、已結案」，可自由切換，不限制順序。選項集中於 `app.py` 的 `STATUSES`，後台使用同一份設定。

「待審核」可不填負責人；其他四種狀態必須填寫，純空白不算有效姓名。前端及後端皆檢查此規則，儲存失敗會顯示中文訊息，保留輸入且不改動案件資料。

既有 `PATCH /api/tickets/<案件編號>` 路由保留，更新範例：

```json
{"status": "已派工", "assignee": "王技師"}
```

成功回傳 HTTP 200、`message` 及最新 `ticket`；格式、狀態或負責人驗證失敗回傳 HTTP 400，不會只更新其中一個欄位；合法更新但案件不存在回傳 HTTP 404。省略 `assignee` 時保留原負責人，明確傳空字串可在「待審核」時清除指派。`status` 仍須提供，舊值「待處理、已完成」不再接受。

案件回應包含 `assignee`，原公開清單及建立／更新回應排除 `contact_name`、`contact_email`；另設的無保護後台讀取 API 包含聯絡資訊。現有共用清單 API 可讀取維修負責人，前台表格不顯示此欄。系統仍採記憶體儲存，沒有新增資料庫或 Email 通知；實際部署前仍需補登入與權限控制。

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

瀏覽器測試會建立測試案件及更新測試案件狀態，請使用獨立測試伺服器。後端測試包含 21 個正式地點、全部設備與問題選項、舊測試值拒絕、功能 A 與 B。瀏覽器測試檢查選單順序與唯一值、中文顯示、其他欄位清除及停用、前後台表格與狀態指派；手機排版仍需人工確認。
