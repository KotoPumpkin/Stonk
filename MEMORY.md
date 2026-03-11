# Stonk 开发进度跟踪表

**项目名称**：Stonk - 股票模拟交易系统  
**项目类型**：C/S 架构 Windows 桌面应用  
**项目状态**：规划阶段  
**最后更新**：2026-03-11

---

## 一、项目需求总览

### 系统三大角色
1. **管理员** (Server 端一体化) - 最高权限，管理房间、股票、机器人
2. **真人账户** (Client 端) - 登录后进入大厅加入房间，执行交易
3. **机器人账户** (虚拟交易者) - 由服务器自动生成，遵循策略规则

### 核心功能模块
- 房间隔离与多人联机
- 步进控制与快进功能
- 股票交易与资产管理
- 机器人策略与自动交易
- 新闻与财报发布系统
- 管理员干预与参数调整

---

## 二、开发阶段规划

### 🔵 Phase 1：基础架构 (当前阶段)

#### 任务列表
- [x] **Task 1.1** 项目目录结构搭建
  - [x] 创建 server/ 包结构
  - [x] 创建 client/ 包结构
  - [x] 创建 shared/ 共享包
  - [x] 创建 requirements.txt
  - [x] 创建 README.md
  
- [x] **Task 1.2** 数据模型定义 (models.py)
  - [x] User 表 - 用户账户信息
  - [x] Room 表 - 房间配置
  - [x] Stock 表 - 股票基础数据
  - [x] Robot 表 - 机器人账户
  - [x] TradeRecord 表 - 交易记录
  - [x] Asset 表 - 资产快照
  - [x] News 表 - 新闻记录
  - [x] Report 表 - 财报记录
  
- [x] **Task 1.3** WebSocket 通信框架 (完成)
  - [x] constants.py - 常量与枚举定义
  - [x] message_protocol.py - 消息协议工厂与解析
  - [x] utils.py - 工具函数（密码加密、ID生成、时间戳）
  - [x] server/config.py - 服务器配置
  - [x] client/config.py - 客户端配置
  - [x] websocket_server.py - 服务器主程序
  - [x] websocket_client.py - 客户端通信
  
- [x] **Task 1.4** 用户认证与会话管理
  - [x] 密码加密存储 (SHA-256 + Salt)
  - [x] 用户注册逻辑
  - [x] 登录验证逻辑
  - [x] 会话管理与 token 刷新
  
- [x] **Task 1.5** 客户端基础 UI 框架
  - [x] login_window.py - 登录界面
  - [x] lobby_window.py - 大厅界面
  - [x] main_window.py - 主窗口容器
  - [x] 基础样式与主题配置

#### 完成度：100%（Phase 1 全部完成）

---

### 🟢 Phase 2：核心交易逻辑 (已完成)

#### 任务列表
- [x] **Task 2.1** 价格生成引擎 (price_engine.py)
  - [x] 随机游走模型
  - [x] 均值回归模型
  - [x] 趋势跟踪模型
  - [x] 动态波动率调整
  - [x] 新闻情绪修正
  
- [x] **Task 2.2** 交易撮合引擎 (trade_manager.py)
  - [x] 订单簿管理
  - [x] 买卖挂单处理
  - [x] 撮合成交逻辑（简化版：按市价成交）
  - [x] 成交价格计算
  
- [x] **Task 2.3** 步进控制逻辑 (step_controller.py)
  - [x] 步进状态管理（多房间架构）
  - [x] 协同确认机制（决策期 + 用户就绪）
  - [x] 快进功能实现（快进循环 + 状态恢复）
  - [x] 暂停/恢复控制
  
- [x] **Task 2.4** 交易界面 (trading_window.py + chart_widgets.py)
  - [x] K 线图显示 (QtCharts QCandlestickSeries + MA5/10/20 均线)
  - [x] 折线图显示 (QLineSeries，秒级步进自动切换)
  - [x] 技术指标叠加 (MACD、KDJ、RSI，可切换子图)
  - [x] 下单界面 (买入/卖出/预估金额/市价显示)
  - [x] 持仓列表 (代码/数量/成本价/现价/市值/浮盈)
  - [x] 资产概览 (总资产/现金/盈亏/盈亏比)
  - [x] 活跃订单列表 (含取消按钮)
  - [x] 快讯面板 (HTML 格式新闻流)
  - [x] 图表类型切换 (K线图/折线图)
  - [x] 决策模式/快进模式控制
  - [x] 退出房间功能

#### 完成度：100%（Phase 2 全部完成）

---

### 🟡 Phase 3：机器人与策略 (待进行)

#### 任务列表
- [ ] **Task 3.1** 策略引擎 (strategy_engine.py)
  - [ ] 散户游资策略实现
  - [ ] 正规机构策略实现
  - [ ] 做空/做多组织策略实现
  - [ ] 策略参数动态调整
  
- [ ] **Task 3.2** 机器人管理 UI
  - [ ] 机器人列表显示
  - [ ] 批量添加机器人
  - [ ] 策略分配与切换
  - [ ] 资金规模修改
  - [ ] 实时参数调整

#### 完成度：0%

---

### 🟡 Phase 4：管理员干预系统 (待进行)

#### 任务列表
- [ ] **Task 4.1** 新闻发布系统
  - [ ] 新闻编辑器
  - [ ] 情绪值设置
  - [ ] 即时广播机制
  - [ ] 策略权重修正
  - [ ] 价格参数修正
  
- [ ] **Task 4.2** 财报发布系统
  - [ ] 财报周期探测
  - [ ] 财报编辑器
  - [ ] 财报数据存储
  - [ ] 长期影响计算
  
- [ ] **Task 4.3** 管理员 UI (admin_ui.py)
  - [ ] 多标签页布局
  - [ ] 房间管理面板
  - [ ] 股票管理工具
  - [ ] 机器人管理工具
  - [ ] 新闻发布器
  - [ ] 参数干预工具

#### 完成度：0%

---

### 🟡 Phase 5：优化与打磨 (待进行)

#### 任务列表
- [ ] **Task 5.1** 性能优化
  - [ ] 数据库查询优化
  - [ ] 网络通信优化
  - [ ] UI 渲染性能
  
- [ ] **Task 5.2** 完整测试覆盖
  - [ ] 单元测试 (核心引擎)
  - [ ] 集成测试 (WebSocket 通信)
  - [ ] UI 功能测试
  - [ ] 压力测试
  
- [ ] **Task 5.3** 文档与部署
  - [ ] API 文档补充
  - [ ] 开发者指南
  - [ ] 用户手册
  - [ ] 打包与部署脚本

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

### 3.2 已定义消息类型 (更新中)

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
- `ADMIN_ADD_ROBOT` - 添加机器人
- `ADMIN_SET_ROBOT_PARAM` - 修改机器人参数
- `ADMIN_PRICE_INTERVENTION` - 价格干预

---

## 四、数据库表结构概览

### 4.1 Users 表
```
id (PK)
username (UNIQUE, NOT NULL)
password_hash (SHA-256 + Salt)
salt
created_at
updated_at
```

### 4.2 Rooms 表
```
id (PK)
name (NOT NULL)
step_mode (秒/时/天/月)
status (运行中/暂停/快进中/已完成)
created_at
updated_at
initial_capital
```

### 4.3 Stocks 表
```
id (PK)
code (UNIQUE, NOT NULL)
name (NOT NULL)
initial_price
issued_shares
description
```

### 4.4 Robots 表
```
id (PK)
room_id (FK)
name
strategy_type (散户游资/正规机构/做空/做多)
initial_capital
current_cash
holdings (JSON)
```

### 4.5 TradeRecords 表
```
id (PK)
room_id (FK)
user_id (FK)
stock_id (FK)
action (买/卖)
quantity
price
timestamp
```

### 4.6 Assets 表
```
id (PK)
room_id (FK)
user_id (FK)
timestamp
cash
holdings (JSON)
total_value
profit_loss
```

### 4.7 News 表
```
id (PK)
room_id (FK)
title
content
sentiment (积极/消极/中立)
affected_stocks (JSON，全局为空)
published_at
```

### 4.8 Reports 表
```
id (PK)
room_id (FK)
stock_id (FK)
pe_ratio
roe
net_income
revenue
manager_weight (管理员设定的策略影响权重)
published_at
```

---

## 五、关键技术决策

### 5.1 已确定
- ✅ 使用 Python asyncio 实现异步服务器
- ✅ 使用 WebSocket + JSON 进行通信
- ✅ 使用 SQLite 存储数据
- ✅ 使用 PySide6 实现 UI
- ✅ 使用 QtCharts 实现图表
- ✅ 密码存储采用 SHA-256 + Salt

### 5.2 待确定
- ⏳ 图表更新频率（秒级步进时是否实时更新）
- ⏳ 大厅房间列表的同步机制
- ⏳ 快进速度参数的具体范围

---

## 六、已知问题与改进方向

### 6.1 已知问题
- [ ] 缺少详细的错误恢复机制
- [ ] 快进期间的网络延迟处理需要优化
- [ ] 图表渲染性能在数据量大时可能下降

### 6.2 改进方向
- [ ] 添加分布式存储支持（支持多进程/多机器部署）
- [ ] 支持离线模式（本地模拟）
- [ ] 添加回放功能（观看历史行情）

---

## 七、协作与沟通记录

### 7.1 设计文档
- **2026-03-11**：初始化 .clineRules 和 MEMORY.md，确立全局开发准则

### 7.2 会议/讨论
（暂无）

### 7.3 风险评估
| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|---------|
| WebSocket 连接断开 | 中 | 高 | 实现自动重连与状态恢复 |
| 数据库并发冲突 | 低 | 中 | 使用事务与锁机制 |
| UI 界面卡顿 | 中 | 中 | 优化渲染与异步操作 |

---

## 八、待办事项总结

### 立即需要完成
1. [x] 创建完整的项目目录结构
2. [x] 编写 requirements.txt
3. [x] 初始化 shared/ 模块（常量、协议、工具函数）
4. [x] 编写服务器/客户端配置文件
5. [x] 编写项目 README.md

### 第一周优先级
1. [ ] 完成 models.py 数据模型（User、Room、Stock、Robot 等表）
2. [ ] 实现 WebSocket 服务器框架（连接管理、消息分发）
3. [ ] 实现 WebSocket 客户端（连接、心跳、消息处理）
4. [ ] 实现用户认证与会话管理

### 第二周优先级
1. [ ] 完成价格生成引擎基础版（随机游走模型）
2. [ ] 完成交易撮合逻辑（订单簿、成交撮合）
3. [ ] 实现步进控制逻辑
4. [ ] 实现客户端基础 UI（登录、大厅、交易窗口框架）

---

**文档版本**：1.1  
**最后更新**：2026-03-11 下午 14:44
**维护人员**：Development Team

---

## 九、Phase 1 完成总结

### 已完成的工作
1. ✅ **数据模型层** - 完整的异步数据库操作封装
2. ✅ **WebSocket 通信** - 服务器和客户端双向通信框架
3. ✅ **用户认证** - 安全的密码存储和会话管理
4. ✅ **客户端 UI** - 完整的登录、大厅、主窗口框架
5. ✅ **单元测试** - 24 个测试用例，全部通过

### 测试结果
```
test_shared.py:  18 tests - OK (密码加密、消息协议、ID生成)
test_models.py:   6 tests - OK (数据库操作、会话管理)
Total:           24 tests - PASSED
```

### 架构特点
- **异步架构**：使用 Python asyncio 和 aiosqlite 实现完全异步非阻塞
- **消息驱动**：WebSocket 消息协议完全定义和验证
- **安全认证**：SHA-256 + Salt 密码加密，Token 会话管理
- **模块化设计**：清晰的目录结构，易于扩展

### 下一步 (Phase 2)
- 价格生成引擎
- 交易撮合逻辑
- 步进控制系统
- 交易界面（K 线图、下单面板）

---

## 十、Phase 2 完成总结

### 已完成的工作
1. ✅ **价格生成引擎** (price_engine.py) - 三种价格模型、动态波动率、新闻情绪修正
2. ✅ **交易撮合引擎** (trade_manager.py) - 订单簿、挂单/撮合、账户资产管理
3. ✅ **步进控制器** (step_controller.py) - 多房间管理、决策期协同、快进/暂停
4. ✅ **交易界面** (trading_window.py + chart_widgets.py) - K线图、折线图、技术指标、下单、持仓、资产
5. ✅ **完整单元测试** - 96 个 Phase 2 测试用例，全部通过

### 测试结果
```
test_price_engine.py:        15 tests - OK (三种价格模型、波动率、新闻情绪)
test_trade_manager.py:       23 tests - OK (账户、下单、撮合、持仓、盈亏)
test_step_controller.py:     27 tests - OK (房间管理、步进、快进、暂停)
test_phase2_integration.py:  10 tests - OK (完整流程、多步交易、回调)
test_chart_widgets.py:       21 tests - OK (EMA/SMA/MACD/KDJ/RSI、数据结构)
Total Phase 2:               96 tests - PASSED
Total All:                  120 tests - PASSED (Phase 1 + Phase 2)
```

### 新增文件
- **client/ui/chart_widgets.py** - 图表组件模块（K线图、折线图、指标子图、技术指标计算器）
- **client/ui/trading_window.py** - 交易窗口主体（重写，集成图表和交易面板）
- **tests/test_chart_widgets.py** - 图表组件和技术指标测试

### 架构亮点
- **数据类设计**: 使用 Python dataclass 定义 Order、Trade、Position、Account、OHLCData 等核心数据结构
- **多房间架构**: StepController 支持同时管理多个独立房间
- **异步回调**: 步进控制器支持注册异步回调函数，便于与 WebSocket 集成
- **简化撮合**: 按市价成交所有活跃订单，符合项目规范（无涨跌停、无滑点）
- **图表组件化**: K线图、折线图、指标图独立组件，支持动态切换
- **技术指标**: 完整实现 EMA/SMA/MACD/KDJ/RSI 计算，纯 Python 无外部依赖
- **深色金融风格**: 统一的深色主题，涨红跌绿配色，扁平化设计

### 交易界面功能清单
| 功能 | 描述 |
|------|------|
| K线图 | QCandlestickSeries + MA5/10/20 均线叠加 |
| 折线图 | QLineSeries，秒级步进自动切换 |
| MACD | DIF/DEA 线 + 柱状图（红涨绿跌） |
| KDJ | K/D/J 三线 |
| RSI | RSI 线 + 超买(80)/超卖(20) 参考线 |
| 下单面板 | 代码输入、数量选择、市价显示、预估金额 |
| 持仓列表 | 代码/数量/成本价/现价/市值/浮盈 |
| 资产概览 | 总资产/现金/盈亏/盈亏比 |
| 活跃订单 | 订单号/代码/方向/数量/价格/取消按钮 |
| 快讯面板 | HTML 格式新闻流 |
| 模式控制 | 决策模式/快进模式/退出房间 |

### 下一步 (Phase 3)
- 策略引擎（散户游资、正规机构、做空/做多组织）
- 机器人管理 UI

---

### 快速链接
- [开发规范](.clineRules)
- [技术栈详情](.clineRules#七技术架构与选型)
- [API 消息协议](MEMORY.md#三核心-api-与消息协议)
