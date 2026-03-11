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

### 🟡 Phase 2：核心交易逻辑 (待进行)

#### 任务列表
- [ ] **Task 2.1** 价格生成引擎 (price_engine.py)
  - [ ] 随机游走模型
  - [ ] 均值回归模型
  - [ ] 趋势跟踪模型
  - [ ] 动态波动率调整
  - [ ] 新闻情绪修正
  
- [ ] **Task 2.2** 交易撮合引擎 (trade_manager.py)
  - [ ] 订单簿管理
  - [ ] 买卖挂单处理
  - [ ] 撮合成交逻辑
  - [ ] 成交价格计算
  
- [ ] **Task 2.3** 步进控制逻辑
  - [ ] 步进状态管理
  - [ ] 协同确认机制
  - [ ] 快进功能实现
  - [ ] 强制托管控制
  
- [ ] **Task 2.4** 交易界面 (trading_window.py)
  - [ ] K 线图显示 (QtCharts)
  - [ ] 折线图显示
  - [ ] 技术指标叠加 (MACD、KDJ)
  - [ ] 下单界面
  - [ ] 持仓列表
  - [ ] 资产概览

#### 完成度：0%

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

### 快速链接
- [开发规范](.clineRules)
- [技术栈详情](.clineRules#七技术架构与选型)
- [API 消息协议](MEMORY.md#三核心-api-与消息协议)
