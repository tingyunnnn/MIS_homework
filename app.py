from datetime import datetime
import re

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 教學用：資料只暫存在記憶體。重新啟動程式後會清空。
tickets = []

# 待確認設定：以下僅供課堂測試，不是正式校園資料。取得清單後集中替換。
FORM_OPTIONS = {
    "buildings": [("test_building", "測試大樓（待確認，非正式資料）")],
    "equipment": [("test_equipment", "測試設備（待確認，非正式資料）"), ("other", "其他")],
    "description": [("test_problem", "測試問題（待確認，非正式資料）"), ("other", "其他")],
}
EMAIL_PATTERN = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+"


def public_ticket(ticket):
    # 清單及更新回應皆不公開聯絡資料；目前後台尚無登入保護。
    return {key: value for key, value in ticket.items()
            if key not in {"contact", "contact_name", "contact_email"}}


@app.get("/")
def index():
    return render_template("index.html", options=FORM_OPTIONS, email_pattern=EMAIL_PATTERN)


@app.get("/admin")
def admin():
    return render_template("admin.html")


@app.get("/api/tickets")
def list_tickets():
    return jsonify([public_ticket(ticket) for ticket in tickets])


@app.post("/api/tickets")
def create_ticket():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "請提供 JSON 物件格式的報修資料"}), 400

    labels = {"building": "大樓", "classroom": "教室／詳細位置",
              "equipment": "設備", "description": "問題描述",
              "contact_name": "姓名", "contact_email": "電子郵件",
              "urgency": "緊急程度"}
    values = {}
    for key, label in labels.items():
        value = data.get(key, "一般" if key == "urgency" else "")
        if not isinstance(value, str) or not value.strip():
            return jsonify({"message": f"請填寫有效的{label}"}), 400
        values[key] = value.strip()

    for key, option_key in [("building", "buildings"), ("equipment", "equipment"),
                            ("description", "description")]:
        if values[key] not in dict(FORM_OPTIONS[option_key]):
            return jsonify({"message": f"請選擇有效的{labels[key]}"}), 400
    if values["urgency"] not in {"一般", "急件", "緊急"}:
        return jsonify({"message": "緊急程度不正確"}), 400
    if not re.fullmatch(EMAIL_PATTERN, values["contact_email"]):
        return jsonify({"message": "電子郵件格式不正確，請輸入例如 name@example.com"}), 400

    for key in ("equipment", "description"):
        custom_key = f"{key}_other"
        values[custom_key] = ""
        if values[key] == "other":
            custom = data.get(custom_key, "")
            if not isinstance(custom, str) or not custom.strip():
                return jsonify({"message": f"選擇其他時，請填寫自訂{labels[key]}"}), 400
            values[custom_key] = custom.strip()

    equipment = values["equipment_other"] or dict(FORM_OPTIONS["equipment"])[values["equipment"]]
    description = values["description_other"] or dict(FORM_OPTIONS["description"])[values["description"]]

    ticket = {
        "id": f"T-{len(tickets) + 1:03d}",
        **values,
        "equipment_type": values["equipment"],
        "description_type": values["description"],
        "location": f'{dict(FORM_OPTIONS["buildings"])[values["building"]]} {values["classroom"]}',
        "equipment": equipment,
        "description": description,
        "status": "待處理",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    tickets.append(ticket)

    return jsonify(
        {
            "message": f"報修已建立，案件編號為 {ticket['id']}",
            "ticket": public_ticket(ticket),
        }
    ), 201


@app.patch("/api/tickets/<ticket_id>")
def update_ticket(ticket_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "請提供 JSON 物件格式的更新資料"}), 400
    status = data.get("status", "")
    if not isinstance(status, str):
        return jsonify({"message": "案件狀態不正確"}), 400
    status = status.strip()
    allowed_statuses = {"待處理", "處理中", "已完成"}

    if status not in allowed_statuses:
        return jsonify({"message": "案件狀態不正確"}), 400

    ticket = next((item for item in tickets if item["id"] == ticket_id), None)
    if ticket is None:
        return jsonify({"message": "找不到指定案件"}), 404

    ticket["status"] = status
    return jsonify({"message": f"{ticket_id} 已更新為「{status}」", "ticket": public_ticket(ticket)})


if __name__ == "__main__":
    app.run(debug=True)
