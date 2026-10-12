from datetime import datetime
import re

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 教學用：資料只暫存在記憶體。重新啟動程式後會清空。
tickets = []
STATUSES = ("待審核", "已派工", "處理中", "等待零件", "已結案")

# 正式選項集中管理：value 為穩定識別碼，標籤保留完整地點名稱及指定順序。
FORM_OPTIONS = {
    "buildings": [
        ("liberal_arts_la", "文學院大樓 LA"),
        ("fine_arts_fa", "藝術大樓 FA"),
        ("science_east_sc", "理學院及東綜合大樓 SC"),
        ("bioscience_bi", "生科館 BI"),
        ("physics_ph", "物理館 PH"),
        ("chemistry_ch", "化學館 CH"),
        ("materials_ms", "材料大樓 MS"),
        ("electrical_ec", "電資大樓 EC"),
        ("mechanical_en", "機電大樓 EN"),
        ("management_cm", "管理學院 CM"),
        ("marine_engineering_me", "海工館 ME"),
        ("marine_research_ma", "海科研究大樓及實驗大樓 MA"),
        ("marine_resources_mb", "海資館 MB"),
        ("social_sciences_ss", "社會科學院 SS"),
        ("siwan_library_10f_sw", "西灣學院 圖資10F SW"),
        ("siwan_general_ge", "西灣學院 綜合大樓 GE"),
        ("library_3f_il", "圖資3樓 IL"),
        ("library_9f_il", "圖資9樓 IL"),
        ("library_3_to_8f", "圖書館(3~8樓)"),
        ("international_ir", "國際研究大樓 IR"),
        ("library_computer_b1_il_pc", "圖資大樓 電腦教室B1 IL PC"),
    ],
    "equipment": [
        ("projector", "投影機"),
        ("computer", "電腦"),
        ("air_conditioner", "冷氣"),
        ("microphone", "麥克風"),
        ("network_equipment", "網路設備"),
        ("other", "其他"),
    ],
    "description": [
        ("cannot_power_on", "無法開機"),
        ("malfunction", "無法正常運作"),
        ("connection_issue", "連線異常"),
        ("damaged", "設備損壞"),
        ("other", "其他"),
    ],
}
EMAIL_PATTERN = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)+"


def public_ticket(ticket):
    # 原公開 API、建立及更新回應排除聯絡資料；後台另有無保護的讀取 API。
    return {key: value for key, value in ticket.items()
            if key not in {"contact", "contact_name", "contact_email"}}


@app.get("/")
def index():
    return render_template("index.html", options=FORM_OPTIONS, email_pattern=EMAIL_PATTERN)


@app.get("/admin")
def admin():
    return render_template("admin.html", statuses=STATUSES)


@app.get("/api/tickets")
def list_tickets():
    return jsonify([public_ticket(ticket) for ticket in tickets])


@app.get("/api/admin/tickets")
def list_admin_tickets():
    # 尚無登入或存取保護，僅供本機課堂展示，務必使用虛構資料。
    return jsonify(tickets)


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
        "status": "待審核",
        "assignee": "",
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
    if status not in STATUSES:
        return jsonify({"message": "案件狀態不正確"}), 400

    ticket = next((item for item in tickets if item["id"] == ticket_id), None)
    if ticket is None:
        return jsonify({"message": "找不到指定案件"}), 404

    # PATCH 未提供負責人時保留原值；有提供空字串則表示清除指派。
    assignee = data.get("assignee", ticket.get("assignee", ""))
    if not isinstance(assignee, str):
        return jsonify({"message": "維修負責人必須為姓名文字"}), 400
    assignee = assignee.strip()
    if status != "待審核" and not assignee:
        return jsonify({"message": f"「{status}」必須填寫維修負責人"}), 400

    # 所有驗證通過後才更新，避免驗證失敗造成部分寫入。
    ticket.update(status=status, assignee=assignee)
    return jsonify({"message": f"{ticket_id} 已更新為「{status}」", "ticket": public_ticket(ticket)})


if __name__ == "__main__":
    app.run(debug=True)
