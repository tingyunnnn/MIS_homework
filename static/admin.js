const table = document.querySelector("#ticket-table");
const tableBody = table.querySelector("tbody");
const emptyState = document.querySelector("#empty-state");
const message = document.querySelector("#message");
const refreshButton = document.querySelector("#refresh-button");
const statuses = JSON.parse(table.dataset.statuses);

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function addCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.appendChild(cell);
  return cell;
}

function createStatusSelect(currentStatus) {
  const select = document.createElement("select");
  for (const status of statuses) {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = status;
    option.selected = status === currentStatus;
    select.appendChild(option);
  }
  return select;
}

function renderTickets(tickets) {
  tableBody.replaceChildren();
  emptyState.hidden = tickets.length > 0;
  table.hidden = tickets.length === 0;

  for (const ticket of tickets) {
    const row = document.createElement("tr");
    addCell(row, ticket.id);
    addCell(row, `${ticket.location}／${ticket.equipment}`);
    addCell(row, ticket.description);
    addCell(row, ticket.created_at);
    addCell(row, ticket.contact_name || "");
    addCell(row, ticket.contact_email || "");

    const statusCell = document.createElement("td");
    const select = createStatusSelect(ticket.status);
    select.setAttribute("aria-label", `${ticket.id} 處理狀態`);
    statusCell.appendChild(select);
    row.appendChild(statusCell);

    const assigneeCell = document.createElement("td");
    const assigneeInput = document.createElement("input");
    assigneeInput.type = "text";
    assigneeInput.value = ticket.assignee || "";
    assigneeInput.setAttribute("aria-label", `${ticket.id} 維修負責人`);
    function syncAssigneeRule() {
      assigneeInput.required = select.value !== "待審核";
      assigneeInput.setCustomValidity("");
    }
    select.addEventListener("change", syncAssigneeRule);
    assigneeInput.addEventListener("input", () => assigneeInput.setCustomValidity(""));
    syncAssigneeRule();
    assigneeCell.appendChild(assigneeInput);
    row.appendChild(assigneeCell);

    const actionCell = document.createElement("td");
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.textContent = "儲存案件";
    saveButton.addEventListener("click", async () => {
      const assignee = assigneeInput.value.trim();
      if (select.value !== "待審核" && !assignee) {
        const error = `「${select.value}」必須填寫維修負責人`;
        assigneeInput.setCustomValidity(error);
        assigneeInput.reportValidity();
        showMessage(error, true);
        return;
      }
      assigneeInput.setCustomValidity("");
      saveButton.disabled = true;
      try {
        await updateTicket(ticket.id, select.value, assignee);
      } finally {
        saveButton.disabled = false;
      }
    });
    actionCell.appendChild(saveButton);
    row.appendChild(actionCell);
    tableBody.appendChild(row);
  }
}

async function loadTickets() {
  try {
    // 此資料 API 尚無存取保護，僅供本機以虛構資料展示。
    const response = await fetch("/api/admin/tickets");
    if (!response.ok) throw new Error("無法讀取案件清單");
    renderTickets(await response.json());
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function updateTicket(ticketId, status, assignee) {
  try {
    const response = await fetch(`/api/tickets/${ticketId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, assignee }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || "更新狀態失敗");
    showMessage(result.message);
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
}

refreshButton.addEventListener("click", loadTickets);
loadTickets();
