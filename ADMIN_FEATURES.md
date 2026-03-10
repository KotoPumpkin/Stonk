# 管理功能使用文档

本文档介绍了新增的三个管理功能：股票描述编辑、年度财报发布和新闻系统。

## 功能概览

1. **股票描述模块**：管理员可以为每支股票添加详细的公司描述信息
2. **年度财报系统**：当时间推进满一年时，强制要求管理员为所有股票发布财报
3. **新闻系统**：管理员可以发布影响机器人投资情绪的新闻

## 一、股票描述模块

### 功能说明
- 每支股票可以设置详细的公司描述（如主营业务、行业地位等）
- 管理员可以随时编辑股票描述
- 描述信息会在初始化数据时自动填充

### 使用方法

#### 方法1：使用管理工具脚本
```bash
python admin_tools.py
```
选择 `2. 编辑股票描述`，然后按提示操作。

#### 方法2：通过WebSocket API
发送编辑股票描述的请求：
```json
{
    "action": "edit_stock_description",
    "stock_code": "SH600000",
    "description": "新的股票描述内容"
}
```

### 数据库字段
- `Stock.description`：TEXT类型，存储股票描述信息

---

## 二、年度财报系统

### 功能说明
- 当系统时间推进满一年时，自动触发财报发布要求
- 必须为**所有活跃股票**发布当年财报后，系统才能继续推进
- 财报内容包括：营业收入、净利润、每股收益(EPS)、净资产收益率(ROE)、财报摘要

### 工作流程

#### 1. 检测财报需求
系统在每次步进时自动检测：
- 如果年份发生变化（例如从2024年跨到2025年）
- 系统会设置 `requires_financial_report = True`
- 阻止继续步进，直到所有财报发布完成

#### 2. 发布财报
```bash
python admin_tools.py
```
选择 `3. 发布年度财报`

系统会引导你为每支股票输入：
- 营业收入（亿元）
- 净利润（亿元）
- 每股收益（元）
- 净资产收益率（%）
- 财报摘要

#### 3. WebSocket API方式
```json
{
    "action": "publish_financial_report",
    "stock_code": "SH600000",
    "report_year": 2024,
    "revenue": 500.5,
    "net_profit": 80.3,
    "eps": 1.25,
    "roe": 15.6,
    "summary": "2024年度业绩稳定增长，营收同比增长10%..."
}
```

#### 4. 完成发布
当所有股票的财报都发布后：
- `requires_financial_report` 自动设置为 `False`
- `last_report_year` 更新为当前年份
- 系统可以继续步进

### 数据库表
**FinancialReport**：
- `stock_id`：关联的股票ID
- `report_year`：财报年份
- `revenue`：营业收入
- `net_profit`：净利润
- `eps`：每股收益
- `roe`：净资产收益率
- `summary`：财报摘要
- `published_at`：发布时间

---

## 三、新闻系统

### 功能说明
- 管理员可以创建影响机器人投资情绪的新闻
- 新闻可以针对特定股票或整个市场
- 新闻在创建后的下一步开始时发布
- 所有用户（包括机器人）必须确认收到新闻后才能继续交易

### 新闻类型
- **POSITIVE（积极）**：利好消息，提升投资情绪
- **NEGATIVE（消极）**：利空消息，降低投资情绪
- **NEUTRAL（中性）**：中性消息，不影响投资情绪

### 影响强度
- 范围：-1.0 到 1.0
- 负数表示消极影响
- 正数表示积极影响
- 绝对值越大影响越强

### 使用流程

#### 1. 创建新闻
```bash
python admin_tools.py
```
选择 `4. 创建新闻`

按提示输入：
1. 选择关联股票（或选择0创建全市场新闻）
2. 输入新闻标题
3. 输入新闻内容
4. 选择影响类型（积极/消极/中性）
5. 输入影响强度

示例：
```
选择股票: 2. SH600519 - 贵州茅台
新闻标题: 茅台销量大幅增长
新闻内容: 贵州茅台公布最新数据，本季度销量同比增长30%，市场需求旺盛
影响类型: 1 (积极)
影响强度: 0.6
```

#### 2. 新闻发布
- 新闻创建后处于**待发布**状态
- 在下一步操作开始时，系统自动发布所有待发布的新闻
- 所有用户必须确认收到新闻

#### 3. WebSocket API方式

**创建新闻：**
```json
{
    "action": "create_news",
    "stock_code": "SH600519",  // 可选，不填则为全市场新闻
    "title": "茅台销量大幅增长",
    "content": "贵州茅台公布最新数据...",
    "impact_type": "POSITIVE",
    "impact_score": 0.6
}
```

**确认收到新闻：**
```json
{
    "action": "confirm_news",
    "news_id": 1
}
```

**查询待确认的新闻：**
```json
{
    "action": "get_pending_news"
}
```

响应：
```json
{
    "status": "success",
    "pending_news": [
        {
            "id": 1,
            "stock_code": "SH600519",
            "stock_name": "贵州茅台",
            "title": "茅台销量大幅增长",
            "content": "贵州茅台公布最新数据...",
            "impact_type": "POSITIVE",
            "impact_score": 0.6,
            "published_at": "2024-01-15 09:30:00"
        }
    ]
}
```

### 机器人投资情绪影响

新闻会影响机器人的投资决策：

1. **积极新闻** (impact_score > 0)
   - 增加买入概率
   - 减少卖出概率
   - 影响持续一定步数

2. **消极新闻** (impact_score < 0)
   - 减少买入概率
   - 增加卖出概率
   - 可能触发止损

3. **中性新闻** (impact_score = 0)
   - 仅作为信息展示
   - 不影响投资决策

### 数据库表

**News**：
- `stock_id`：关联的股票ID（可为NULL，表示全市场新闻）
- `title`：新闻标题
- `content`：新闻内容
- `impact_type`：影响类型（POSITIVE/NEGATIVE/NEUTRAL）
- `impact_score`：影响强度（-1.0 到 1.0）
- `is_published`：是否已发布
- `created_at`：创建时间
- `published_at`：发布时间

**NewsConfirmation**：
- `news_id`：新闻ID
- `user_id`：用户ID
- `confirmed_at`：确认时间

---

## 系统状态扩展

`SystemState` 表新增字段：

- `last_report_year`：上次发布财报的年份
- `requires_financial_report`：是否需要发布财报（布尔值）
- `has_pending_news`：是否有待发布的新闻（布尔值）

---

## 完整工作流示例

### 场景：时间推进到新的一年

1. **系统检测到年份变化**
   ```
   2024-12-31 → 2025-01-01
   ```

2. **触发财报要求**
   ```
   requires_financial_report = True
   系统阻止继续步进
   ```

3. **管理员发布财报**
   ```bash
   python admin_tools.py
   选择 3. 发布年度财报
   为每支股票输入2024年度财报数据
   ```

4. **管理员创建新年新闻**
   ```bash
   python admin_tools.py
   选择 4. 创建新闻
   创建"新年开市"相关新闻
   ```

5. **下一步操作**
   - 新闻自动发布
   - 所有用户收到新闻提示
   - 用户确认后才能进行交易

6. **系统恢复正常**
   ```
   requires_financial_report = False
   has_pending_news = False (用户确认后)
   系统可以继续步进
   ```

---

## 注意事项

1. **财报发布是强制性的**
   - 如果未完成财报发布，系统无法继续步进
   - 必须为所有活跃股票发布财报

2. **新闻确认机制**
   - 所有用户（包括机器人）必须确认收到新闻
   - 未确认用户无法进行交易操作
   - 机器人会自动确认新闻

3. **数据持久化**
   - 所有股票描述、财报、新闻数据都保存在数据库中
   - 可以随时查询历史数据

4. **影响范围**
   - 股票描述：仅供查看，不影响交易
   - 财报：阻塞系统推进，影响全局
   - 新闻：影响机器人决策，需用户确认

---

## 常见问题

### Q1: 如何查看某支股票的历史财报？
```bash
python admin_tools.py
选择 6. 查看历史财报
输入年份
```

### Q2: 如何删除或修改已发布的新闻？
新闻一旦发布无法删除，但可以发布更正新闻。

### Q3: 财报发布后能否修改？
财报发布后无法直接修改，建议在发布前仔细核对数据。

### Q4: 新闻影响持续多久？
新闻影响会随时间衰减，具体持续时长在 `strategy_engine.py` 中配置。

### Q5: 如何重置系统重新开始？
```bash
python init_data.py --reset
```
注意：这会删除所有数据包括财报和新闻。

---

## 开发者接口

如需在自己的应用中集成这些功能，可参考 `admin_tools.py` 中的函数：

- `list_stocks()` - 列出股票
- `edit_stock_description()` - 编辑描述
- `publish_financial_report()` - 发布财报
- `create_news()` - 创建新闻
- `view_pending_news()` - 查看待发布新闻
- `view_financial_reports()` - 查看历史财报

也可以通过 WebSocket API 与 `websocket_server.py` 交互。
