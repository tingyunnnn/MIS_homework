from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 教學用：資料只暫存在記憶體。重新啟動程式後會清空。
tickets = []


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/admin")
def admin():
    return render_template("admin.html")


@app.get("/api/tickets")
def list_tickets():
    return jsonify(tickets)


@app.post("/api/tickets")
def create_ticket():
    data = request.get_json(silent=True) or {}

    location = str(data.get("location", "")).strip()
    equipment = str(data.get("equipment", "")).strip()
    description = str(data.get("description", "")).strip()
    urgency = str(data.get("urgency", "一般")).strip()
    contact = str(data.get("contact", "")).strip()

    missing = []
    if not location:
        missing.append("地點")
    if not equipment:
        missing.append("設備")
    if not description:
        missing.append("問題描述")
    if not contact:
        missing.append("聯絡方式")

    if missing:
        return jsonify({"message": f"請填寫：{'、'.join(missing)}"}), 400

    ticket = {
        "id": f"T-{len(tickets) + 1:03d}",
        "location": location,
        "equipment": equipment,
        "description": description,
        "urgency": urgency or "一般",
        "contact": contact,
        "status": "待處理",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    tickets.append(ticket)

    return jsonify(
        {
            "message": f"報修已建立，案件編號為 {ticket['id']}",
            "ticket": ticket,
        }
    ), 201


@app.patch("/api/tickets/<ticket_id>")
def update_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).strip()
    allowed_statuses = {"待處理", "處理中", "已完成"}

    if status not in allowed_statuses:
        return jsonify({"message": "案件狀態不正確"}), 400

    ticket = next((item for item in tickets if item["id"] == ticket_id), None)
    if ticket is None:
        return jsonify({"message": "找不到指定案件"}), 404

    ticket["status"] = status
    return jsonify({"message": f"{ticket_id} 已更新為「{status}」", "ticket": ticket})


if __name__ == "__main__":
    app.run(debug=True)
