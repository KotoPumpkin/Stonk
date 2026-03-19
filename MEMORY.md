# Stonk 开发进度跟踪表

**项目名称**：Stonk - 股票模拟交易系统  
**项目类型**：C/S 架构 Windows 桌面应用  
**项目状态**：Phase 4 已完成，准备进入 Phase 5  
**最后更新**：2026-03-13

---

## 一、项目需求总览

### 系统三大角色
1. **管理员** (Server 端一体化) - 最高权限，管理房间、股票、机器人
2. **真人账户** (Client 端) - 登录后进入大厅加入房间，执行交易
3. **机器人账户** (虚拟交易者) - 由服务器自动生成，遵循策略规则

### 核心功能模块
- ✅ 房间隔离与多人联机
- ✅ 步进控制与快进功能
- ✅ 股票交易与资产管理
- ✅ 机器人策略与自动交易
- ✅ 新闻与财报发布系统
- ✅ 管理员干预与参数调整

---

## 二、开发阶段规划

### 🔵 Phase 1：基础架构 (已完成)

#### 任务列表
- [x] **Task 1.1** 项目目录结构搭建
- [x] **Task 1.2** 数据模型定义 (models.py)
- [x] **Task 1.3** WebSocket 通信框架
- [x] **Task 1.4** 用户认证与会话管理
- [x] **Task 1.5** 客户端基础 UI 框架

#### 完成度：100%

---

### 🟢 Phase 2：核心交易逻辑 (已完成)

#### 任务列表
- [x] **Task 2.1** 价格生成引擎 (price_engine.py)
- [x] **Task 2.2** 交易撮合引擎 (trade_manager.py)
- [x] **Task 2.3** 步进控制逻辑 (step_controller.py)
- [x] **Task 2.4** 交易界面 (trading_window.py + chart_widgets.py)

#### 完成度：100%

---

### 🟡 Phase 3：机器人与策略 (已完成)

#### 任务列表
- [x] **Task 3.1** 策略引擎 (strategy_engine.py)
- [x] **Task 3.2** 机器人管理 UI (robot_management_widget.py)

#### 完成度：100%

---

### 🟢 Phase 4：管理员干预系统 (已完成)

#### 任务列表
- [x] **Task 4.1** 新闻发布系统
- [x] **Task 4.2** 财报发布系统
- [x] **Task 4.3** 管理员 UI (admin_ui.py)
- [x] **Task 4.4** 管理员工具 (admin_tools.py)

#### 完成度：100%

---

### ⚪ Phase 5：优化与打磨 (待进行)

#### 任务列表
- [ ] **Task 5.1** 性能优化
  - [ ] 数据库查询优化
  - [ ] 网络通信优化
  - [ ] UI 渲染性能
  
- [ ] **Task 5.2** 完整测试覆盖
  - [ ] 边界条件测试
  - [ ] 压力测试
  - [ ] UI 自动化测试
  
- [ ] **Task 5.3** 文档与部署
  - [ ] 用户手册
  - [ ] 打包与部署脚本
  - [ ] 发行版本构建

#### 完成度：0%

---

## 三、核心 API 与消息协议

### 3.1 WebSocket 消息基础格式

```json
{
  "type": "MESSAGE_TYPE",
  "data": {
    "key": "value"
  },
  "timestamp": 1234567890,
  "room_id": "optional_room_uuid"
}
```

### 3.2 已定义消息类型

#### 认证相关
- `REGISTER` - 用户注册
- `LOGIN` - 用户登录
- `LOGOUT` - 用户登出
- `HEARTBEAT` - 心跳保活

#### 房间相关
- `CREATE_ROOM` - 创建房间
- `JOIN_ROOM` - 加入房间
- `LEAVE_ROOM` - 离开房间
- `DESTROY_ROOM` - 销毁房间
- `ROOM_LIST` - 房间列表更新

#### 交易相关
- `PLACE_ORDER` - 挂单
- `CANCEL_ORDER` - 取消订单
- `PRICE_UPDATE` - 价格更新
- `TRADE_EXECUTE` - 交易成交
- `ASSET_UPDATE` - 资产更新

#### 步进相关
- `STEP_START` - 步进开始（决策期）
- `STEP_COMPLETE` - 玩家确认步进完成
- `STEP_BROADCAST` - 步进完成广播
- `FAST_FORWARD_START` - 快进开始
- `FAST_FORWARD_STOP` - 快进停止

#### 管理员命令
- `ADMIN_PUBLISH_NEWS` - 发布新闻
- `ADMIN_PUBLISH_REPORT` - 发布财报
- `ADMIN_CREATE_ROBOT` - 创建全局机器人
- `ADMIN_UPDATE_ROBOT` - 更新机器人信息
- `ADMIN_DELETE_ROBOT` - 删除机器人
- `ADMIN_LIST_ROBOTS` - 列出全局机器人
- `ADMIN_SET_ROBOT_STRATEGY` - 设置机器人策略类型
- `ADMIN_ADD_ROBOT_TO_ROOM` - 添加机器人到房间
- `ADMIN_REMOVE_ROBOT_FROM_ROOM` - 从房间移除机器人
- `ADMIN_LIST_ROOM_ROBOTS` - 列出房间机器人

#### 响应类型
- `ROBOT_LIST` - 全局机器人列表响应
- `ROOM_ROBOT_LIST` - 房间机器人列表响应

---

## 四、数据库表结构概览

### 4.1 Users 表
```
id (PK), username (UNIQUE, NOT NULL), password_hash, salt, created_at, updated_at
```

### 4.2 Rooms 表
```
id (PK), name, step_mode, status, created_at, updated_at, initial_capital
```

### 4.3 Stocks 表
```
id (PK), code (UNIQUE), name, initial_price, issued_shares, description
```

### 4.4 Robots 表
```
id (PK), room_id (FK, nullable), name, strategy_type, initial_capital, current_cash, holdings (JSON)
```

### 4.5 TradeRecords 表
```
id (PK), room_id (FK), user_id (FK), stock_id (FK), action, quantity, price, timestamp
```

### 4.6 Assets 表
```
id (PK), room_id (FK), user_id (FK), timestamp, cash, holdings (JSON), total_value, profit_loss
```

### 4.7 News 表
```
id (PK), room_id (FK), title, content, sentiment, affected_stocks (JSON), published_at
```

### 4.8 Reports 表
```
id (PK), room_id (FK), stock_id (FK), pe_ratio, roe, net_income, revenue, manager_weight, published_at
```

---

## 五、技术栈

| 层级 | 技术选型 |
|------|---------|
| 通信协议 | WebSocket + JSON |
| 并发模型 | Python asyncio |
| 前端框架 | PySide6 (Qt for Python) |
| 图表库 | QtCharts |
| 数据库 | SQLite + aiosqlite |
| 安全 | SHA-256 + Salt 密码加密 |

---

## 六、项目文件结构

```
Stonk/
├── server/
│   ├── __init__.py
│   ├── websocket_server.py    # WebSocket 服务器
│   ├── price_engine.py        # 价格生成引擎
│   ├── strategy_engine.py     # 机器人策略引擎
│   ├── trade_manager.py       # 交易撮合引擎
│   ├── step_controller.py     # 步进控制器
│   ├── models.py              # 数据模型和数据库
│   ├── admin_tools.py         # 管理员工具
│   ├── admin_ui.py            # 管理员 UI
│   └── config.py              # 服务器配置
├── client/
│   ├── __init__.py
│   ├── websocket_client.py    # WebSocket 客户端
│   ├── config.py              # 客户端配置
│   └── ui/
│       ├── main_window.py     # 主窗口
│       ├── login_window.py    # 登录窗口
│       ├── lobby_window.py    # 大厅窗口
│       ├── trading_window.py  # 交易窗口
│       ├── chart_widgets.py   # 图表组件
│       ├── widgets.py         # 自定义控件
│       ├── robot_management_widget.py  # 机器人管理
│       └── __init__.py
├── shared/
│   ├── constants.py           # 常量定义
│   ├── message_protocol.py    # 消息协议
│   ├── utils.py               # 工具函数
│   └── __init__.py
├── tests/
│   ├── test_models.py
│   ├── test_shared.py
│   ├── test_price_engine.py
│   ├── test_trade_manager.py
│   ├── test_step_controller.py
│   ├── test_chart_widgets.py
│   ├── test_strategy_engine.py
│   ├── test_admin_tools.py
│   ├── test_phase2_integration.py
│   ├── test_phase3_integration.py
│   ├── test_phase4_integration.py
│   └── __init__.py
├── .clineRules                # 全局开发准则
├── MEMORY.md                  # 本文件
├── NETWORK_CONFIG.md          # 网络配置指南
├── README.md                  # 项目说明
├── requirements.txt           # 依赖列表
├── start_admin.bat / .ps1     # 管理员启动脚本
└── start_client.bat / .ps1    # 客户端启动脚本
```

---

## 七、测试覆盖总结

| 阶段 | 测试文件 | 测试数量 | 状态 |
|------|---------|---------|------|
| Phase 1 | test_shared.py | 18 | ✅ PASSED |
| Phase 1 | test_models.py | 6 | ✅ PASSED |
| Phase 2 | test_price_engine.py | 15 | ✅ PASSED |
| Phase 2 | test_trade_manager.py | 23 | ✅ PASSED |
| Phase 2 | test_step_controller.py | 27 | ✅ PASSED |
| Phase 2 | test_chart_widgets.py | 21 | ✅ PASSED |
| Phase 2 | test_phase2_integration.py | 10 | ✅ PASSED |
| Phase 3 | test_strategy_engine.py | 35 | ✅ PASSED |
| Phase 3 | test_phase3_integration.py | 13 | ✅ PASSED |
| Phase 4 | test_admin_tools.py | 23 | ✅ PASSED |
| Phase 4 | test_phase4_integration.py | 12 | ✅ PASSED |
| **总计** | **11 个测试文件** | **203 个测试用例** | **✅ 全部通过** |

---

## 八、已知问题与改进方向

### 8.1 已知问题
- [ ] 缺少详细的错误恢复机制
- [ ] 快进期间的网络延迟处理需要优化
- [ ] 图表渲染性能在数据量大时可能下降

### 8.2 改进方向
- [ ] 添加分布式存储支持（支持多进程/多机器部署）
- [ ] 支持离线模式（本地模拟）
- [ ] 添加回放功能（观看历史行情）

---

## 九、跨机器网络支持

### 配置方法
1. **环境变量方式**：设置 `STONK_SERVER_HOST` 和 `STONK_SERVER_PORT`
2. **登录界面输入**：直接在客户端 UI 中输入服务器地址

### 服务器配置
- 默认绑定 `0.0.0.0:8765`（所有网络接口）
- 需确保防火墙开放 TCP 端口 8765

### 防火墙配置命令（服务器端）
```powershell
New-NetFirewallRule -DisplayName "Stonk Server" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
```

详细配置请参考 [NETWORK_CONFIG.md](NETWORK_CONFIG.md)

---

## 十、快速链接

- [开发规范](.clineRules)
- [网络配置指南](NETWORK_CONFIG.md)
- [项目说明](README.md)

---

**文档版本**：2.0  
**最后更新**：2026-03-13  
**维护人员**：Development Team
