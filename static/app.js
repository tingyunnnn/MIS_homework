const form = document.querySelector("#ticket-form");
const message = document.querySelector("#message");
const table = document.querySelector("#ticket-table");
const tableBody = table.querySelector("tbody");
const emptyState = document.querySelector("#empty-state");
const refreshButton = document.querySelector("#refresh-button");

function syncOtherField(name) {
  const isOther = form.elements[name].value === "other";
  const input = form.elements[`${name}_other`];
  document.querySelector(`#${name}-other-field`).hidden = !isOther;
  input.disabled = !isOther;
  input.required = isOther;
  if (!isOther) input.value = "";
}

for (const name of ["equipment", "description"]) {
  form.elements[name].addEventListener("change", () => syncOtherField(name));
  syncOtherField(name);
}

// required 不會拒絕純空白字串，補上前端检查；email 格式由 HTML 驗證。
form.addEventListener("input", (event) => event.target.setCustomValidity(""));

function validateForm() {
  for (const input of form.querySelectorAll("input, textarea")) {
    input.setCustomValidity("");
    if (!input.disabled && input.required && !input.value.trim()) {
      input.setCustomValidity("請填寫內容，不能只有空白");
    }
  }
  return form.reportValidity();
}

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function addCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.appendChild(cell);
}

function renderTickets(tickets) {
  tableBody.replaceChildren();
  emptyState.hidden = tickets.length > 0;
  table.hidden = tickets.length === 0;

  for (const ticket of tickets) {
    const row = document.createElement("tr");
    addCell(row, ticket.id);
    addCell(row, ticket.location);
    addCell(row, ticket.equipment);
    addCell(row, ticket.urgency);
    addCell(row, ticket.status);
    addCell(row, ticket.description);
    addCell(row, ticket.created_at);
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateForm()) return;
  showMessage("正在建立報修單…");

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) throw new Error(result.message || "建立報修單失敗");

    showMessage(result.message);
    form.reset();
    syncOtherField("equipment");
    syncOtherField("description");
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
});

refreshButton.addEventListener("click", loadTickets);
loadTickets();
