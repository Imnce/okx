# OKX 永续合约量化自动交易控制台

本项目是一个本地运行的 OKX Demo Trading 量化交易软件 v1。它使用 FastAPI 提供后端 API 和静态 Web 控制台，默认只连接 OKX 模拟盘，内置趋势跟随策略、止盈止损和实盘级风控。

> 这不是投资建议。软件目标是执行和风控自动化，不承诺收益。实盘交易必须自行理解风险。

## 功能

- OKX API v5 REST 客户端，支持签名、Demo Trading header、限频和错误归一化。
- 趋势跟随策略：短/长均线方向判断，固定比例止盈止损。
- 风控：低杠杆、逐仓、单笔风险、最大持仓、每日亏损、连续亏损、急停。
- SQLite 审计：策略信号、订单、风控事件、配置快照、系统日志。
- 本地 Web 控制台：状态、行情、持仓、订单、风控、策略参数、启动/暂停/急停。

## 快速开始

```powershell
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000`。

## OKX 配置

在 `.env` 中填写 OKX Demo Trading API Key：

```env
OKX_ENV=demo
OKX_API_KEY=your_key
OKX_API_SECRET=your_secret
OKX_API_PASSPHRASE=your_passphrase
```

默认环境是 `demo`。即使配置 `live`，v1 也会要求 API 层显式允许，避免误触实盘。

## 测试

```powershell
pytest
```

