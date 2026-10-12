const table = document.querySelector("#ticket-table");
const tableBody = table.querySelector("tbody");
const emptyState = document.querySelector("#empty-state");
const message = document.querySelector("#message");
const refreshButton = document.querySelector("#refresh-button");
const statuses = ["待處理", "處理中", "已完成"];

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
    addCell(row, ticket.contact);
    addCell(row, ticket.description);
    addCell(row, ticket.created_at);

    const statusCell = document.createElement("td");
    const select = createStatusSelect(ticket.status);
    statusCell.appendChild(select);
    row.appendChild(statusCell);

    const actionCell = document.createElement("td");
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.textContent = "儲存狀態";
    saveButton.addEventListener("click", () => updateStatus(ticket.id, select.value));
    actionCell.appendChild(saveButton);
    row.appendChild(actionCell);
    tableBody.appendChild(row);
  }
}

async function loadTickets() {
  try {
    const response = await fetch("/api/tickets");
    if (!response.ok) throw new Error("無法讀取案件清單");
    renderTickets(await response.json());
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function updateStatus(ticketId, status) {
  try {
    const response = await fetch(`/api/tickets/${ticketId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
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
