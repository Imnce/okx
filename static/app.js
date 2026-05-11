const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || response.statusText);
  }
  return response.json();
}

function renderStatus(status) {
  $("state").textContent = status.state;
  $("env").textContent = status.env + (status.has_credentials ? "" : " / no key");
  $("symbol").textContent = status.symbol;
  $("price").textContent = status.latest_price ?? "-";
  $("pnl").textContent = `${status.today_pnl_pct.toFixed(2)}%`;
  $("risk").textContent = status.risk_status;
  $("connection").textContent = status.connection_status;
  $("signal").textContent = JSON.stringify(status.last_signal, null, 2);
  $("positions").textContent = JSON.stringify(status.positions, null, 2);
  $("orders").textContent = JSON.stringify(status.open_orders, null, 2);
}

async function refresh() {
  renderStatus(await api("/api/status"));
}

function formConfig() {
  const data = new FormData($("configForm"));
  const numeric = [
    "short_window",
    "long_window",
    "risk_per_trade_pct",
    "take_profit_pct",
    "stop_loss_pct",
    "leverage",
    "order_size_contracts",
    "max_positions",
  ];
  const config = Object.fromEntries(data.entries());
  for (const key of numeric) {
    config[key] = Number(config[key]);
  }
  config.daily_loss_limit_pct = 3;
  config.max_consecutive_losses = 3;
  return config;
}

async function loadConfig() {
  const config = await api("/api/config");
  for (const [key, value] of Object.entries(config)) {
    const input = document.querySelector(`[name="${key}"]`);
    if (input) input.value = value;
  }
}

$("startBtn").addEventListener("click", async () => {
  renderStatus(await api("/api/start", { method: "POST" }));
});

$("pauseBtn").addEventListener("click", async () => {
  renderStatus(await api("/api/pause", { method: "POST" }));
});

$("stopBtn").addEventListener("click", async () => {
  renderStatus(await api("/api/emergency-stop", { method: "POST" }));
});

$("closeBtn").addEventListener("click", async () => {
  renderStatus(await api("/api/close-positions", { method: "POST" }));
});

$("configForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/config", { method: "PUT", body: JSON.stringify(formConfig()) });
  await refresh();
});

loadConfig().then(refresh);
setInterval(refresh, 3000);

