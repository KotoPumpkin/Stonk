# Stonk - 股票模拟交易系统

一款基于 **C/S 架构** 的 Windows 桌面端股票模拟交易程序。系统支持多房间并行会话，允许管理员干预市场、管理机器人策略，并支持真人用户进行手动交易或量化代理交易。

## 🎯 项目特性

### 三大角色
- **管理员** (Server 端一体化)：最高权限，创建房间、管理股票、控制步进、发布新闻/财报、管控机器人
- **真人账户** (Client 端)：登录后进入大厅加入房间，执行买卖操作、查看盈亏
- **机器人账户** (虚拟交易者)：由服务器自动生成，遵循三种策略类型

### 核心功能
✅ 房间隔离与多人联机  
✅ 四种步进模式（秒/时/天/月）与快进功能  
✅ 双向交易（做多/做空）与简化撮合  
✅ 机器人策略与自动交易  
✅ 新闻与财报发布系统  
✅ 管理员实时干预与参数调整  

## 🛠 技术栈

| 模块 | 技术 |
|------|------|
| **架构** | C/S 架构、WebSocket + JSON |
| **后端** | Python asyncio、SQLite |
| **前端** | PySide6 (Qt for Python) |
| **图表** | QtCharts (K线、折线图、指标) |
| **安全** | SHA-256 + Salt 密码加密 |

## 📦 项目结构

```
Stonk/
├── server/                 # 服务器端包
│   ├── __init__.py
│   ├── config.py           # ✅ 服务器配置
│   ├── websocket_server.py # WebSocket 服务器
│   ├── models.py           # 数据模型
│   ├── price_engine.py     # 价格生成引擎
│   ├── strategy_engine.py  # 机器人策略引擎
│   ├── trade_manager.py    # 交易撮合引擎
│   ├── admin_tools.py      # 管理员工具
│   └── admin_ui.py         # 管理员 UI
├── client/                 # 客户端包
│   ├── __init__.py
│   ├── config.py           # ✅ 客户端配置
│   ├── websocket_client.py # WebSocket 客户端
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── login_window.py
│       ├── lobby_window.py
│       ├── trading_window.py
│       └── widgets.py
├── shared/                 # 共享模块包
│   ├── __init__.py
│   ├── constants.py        # ✅ 常量与枚举定义
│   ├── message_protocol.py # ✅ 消息协议工厂
│   └── utils.py            # ✅ 工具函数（密码、ID、时间戳）
├── .clineRules             # ✅ 全局开发准则
├── MEMORY.md               # ✅ 开发进度跟踪
├── requirements.txt        # ✅ 依赖列表
└── README.md               # ✅ 项目说明
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/KotoPumpkin/Stonk.git
cd Stonk

# 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
# 服务器和管理员 UI 一体化
python -m server.websocket_server
```

### 3. 启动客户端

```bash
# 客户端
python -m client.ui.main_window
```

## 📋 核心概念

### 步进模式

| 模式 | 单位 | 真人操作 | 机器人行为 | 图表 |
|------|------|--------|---------|------|
| 超短线 | 秒 | 禁止（仅观看） | 高频 | 折线图 |
| 较短线 | 小时 | 允许 | 中频 | K线+指标 |
| 短线 | 天 | 允许 | 低频 | K线+指标 |
| 中线 | 月 | 允许 | 按天决策 | K线+指标 |

### 机器人策略

1. **散户游资** (Retail)
   - 高频交易、追涨杀跌
   - 受新闻情绪影响剧烈
   - 换手率高

2. **正规机构** (Institution)
   - 价值导向、低换手率
   - 对财报数据敏感
   - 稳定持仓

3. **做空/做多组织** (Short/Long)
   - 趋势追踪
   - 明显的单边操作倾向
   - 风险承受能力高

## 🔧 配置说明

### 服务器配置 (`server/config.py`)

```python
# WebSocket 服务器
HOST = "localhost"
PORT = 8765

# 房间与用户限制
MAX_ROOMS = 100
MAX_USERS_PER_ROOM = 50

# 交易参数
TRADING_COMMISSION_RATE = 0.001  # 0.1% 手续费
PRICE_VOLATILITY = 0.02           # 2% 波动率
```

### 客户端配置 (`client/config.py`)

```python
# 服务器连接
SERVER_ADDRESS = "localhost"
SERVER_PORT_NUM = 8765

# UI 主题
COLORS = {
    "background": "#1a1a1a",
    "success": "#00ff00",
    "danger": "#ff0000",
}
```

## 📊 共享模块

### Constants (`shared/constants.py`)
定义枚举类型：
- `StepMode` - 步进模式
- `RoomStatus` - 房间状态
- `RobotStrategyType` - 机器人策略
- `OrderDirection` - 订单方向
- `NewsSentiment` - 新闻情绪

### Message Protocol (`shared/message_protocol.py`)
定义消息协议：
- `MessageType` - 所有消息类型枚举
- `create_message()` - 创建消息工厂函数
- `parse_message()` - 解析消息函数
- `validate_message()` - 验证消息有效性

### Utils (`shared/utils.py`)
提供工具函数：
- 密码加密：`hash_password()`, `verify_password()`
- ID 生成：`generate_user_id()`, `generate_room_id()`
- 时间戳：`get_timestamp()`

## 📝 开发阶段

### ✅ Phase 1：基础架构 (当前)
- [x] 项目目录结构
- [x] 共享模块（常量、协议、工具函数）
- [x] 服务器/客户端配置
- [ ] 数据模型定义
- [ ] WebSocket 通信框架
- [ ] 用户认证与会话管理
- [ ] 基础 UI 框架

### 🔜 Phase 2-5
详见 [MEMORY.md](MEMORY.md#二开发阶段规划)

## 📖 文档

- **[.clineRules](.clineRules)** - 全局开发准则与系统设计规范
- **[MEMORY.md](MEMORY.md)** - 开发进度跟踪与 API 文档
- **[PySide6 文档](https://doc.qt.io/qtforpython/)** - UI 框架参考
- **[Python asyncio](https://docs.python.org/3/library/asyncio.html)** - 异步编程参考

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m '[Phase] [Module] 功能描述'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 提交规范

```
[Phase] [Module] 简短描述

详细说明（可选）

关联 Issue: #123
```

## ⚖️ 许可证

MIT License

## 📧 联系方式

- 项目主页：https://github.com/KotoPumpkin/Stonk
- 问题反馈：通过 GitHub Issues

---

**最后更新**：2026-03-11  
**版本**：1.0.0 (Pre-release)
