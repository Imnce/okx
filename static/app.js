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
    "breakout_window",
    "mean_window",
    "mean_reversion_threshold_pct",
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

function metricsHtml(title, metrics) {
  return `
    <div>
      <h4>${title}</h4>
      <div class="metrics">
        <div><span>交易数</span><strong>${metrics.trades}</strong></div>
        <div><span>胜率</span><strong>${metrics.win_rate_pct}%</strong></div>
        <div><span>收益</span><strong>${metrics.total_return_pct}%</strong></div>
        <div><span>回撤</span><strong>${metrics.max_drawdown_pct}%</strong></div>
        <div><span>盈亏比</span><strong>${metrics.profit_factor}</strong></div>
        <div><span>评分</span><strong>${metrics.score}</strong></div>
      </div>
    </div>
  `;
}

function renderBacktest(report) {
  const best = report.recommendation ? `推荐：${report.recommendation.name}` : "没有足够稳健的推荐";
  $("backtestSummary").textContent = `${report.symbol} / ${report.bar} / ${report.candles} 根K线。${best}`;
  $("backtestResults").innerHTML = report.candidates
    .map(
      (candidate) => `
        <article class="candidate">
          <h3>${candidate.name}</h3>
          ${metricsHtml("训练段", candidate.train)}
          ${metricsHtml("样本外", candidate.test)}
          <p class="note">${candidate.anti_overfit_note}</p>
          <button type="button" class="useCandidate" data-config='${JSON.stringify(candidate.config)}'>应用参数</button>
        </article>
      `,
    )
    .join("");
}

$("backtestBtn").addEventListener("click", async () => {
  $("backtestSummary").textContent = "正在获取 OKX XAU-USDT-SWAP 历史K线并回测...";
  const report = await api("/api/backtest/xau?bar=1H&limit=300");
  renderBacktest(report);
});

$("backtestResults").addEventListener("click", async (event) => {
  if (!event.target.classList.contains("useCandidate")) return;
  const config = JSON.parse(event.target.dataset.config);
  for (const [key, value] of Object.entries(config)) {
    const input = document.querySelector(`[name="${key}"]`);
    if (input) input.value = value;
  }
  await api("/api/config", { method: "PUT", body: JSON.stringify(formConfig()) });
  await refresh();
});

loadConfig().then(refresh);
setInterval(refresh, 3000);
