# Auditable Business Metrics Copilot

中文名：可审计经营指标智能问答 Agent

一个可运行的全栈 BI Copilot。业务用户输入自然语言问题，系统会返回业务结果、SQL、指标口径、原始明细和图表，并通过受控 query plan + metric catalog 保证结果可审计。

## 功能概览

- 统一指标目录：所有指标都来自注册的 metric catalog，系统不会虚构新指标。
- 可审计 SQL：所有回答都展示格式化 SQL、Query Plan、过滤条件和时间范围。
- 经营分析能力：支持 YOY、MOM、DOD、MTD、趋势、排名、拆解、简单归因和异常检测。
- 多轮澄清：问题不完整时先追问，不盲猜。
- 双模式输出：每次回答默认同时包含结果模式和代码模式。
- 数据回退：PostgreSQL 不可用时自动切换到内存 mock 数据，`data_source = "fallback_mock"`。

## 项目结构

```text
backend/
  app/
    main.py
    api/
    agents/
    core/
    db/
    metrics/
    services/
    schemas/
  tests/
  Dockerfile
  requirements.txt

frontend/
  src/
    components/
    pages/
    api/
    types/
    utils/
  Dockerfile
  package.json
  vite.config.ts

database/
  init.sql
  seed_data.py

docker-compose.yml
README.md
.env.example
```

## 架构说明

系统按下面的受控链路工作：

```text
自然语言问题
-> 规则化 NLU / 澄清状态机
-> Structured Query Plan
-> Metric Catalog 校验
-> Controlled SQL Builder
-> PostgreSQL 或内存 fallback 执行
-> 指标计算引擎
-> 业务摘要 + SQL + 指标口径 + 原始数据
```

关键模块：

- `backend/app/services/nlu.py`
  负责中文问题识别、意图分类、时间解析和多轮澄清。
- `backend/app/metrics/catalog.json`
  指标语义层，定义指标口径、默认过滤和允许维度。
- `backend/app/services/sql_builder.py`
  只基于白名单表、字段、指标和维度生成 SQL。
- `backend/app/services/metric_service.py`
  负责 YOY / MOM / DOD / MTD / 趋势 / 排名 / 归因 / 异常检测。
- `backend/app/services/data_source.py`
  封装 PostgreSQL 与 fallback mock 的双数据通路。
- `frontend/src/components/AssistantAnswerCard.tsx`
  单条回答的 BI 卡片化展示，包含结果 / 代码 / 指标口径 / 明细数据四个 tab。

## 数据库设计

表名：`fact_delivery_orders`

核心字段：

- `order_id`
- `statistics_date`
- `delivery_time`
- `channel`
- `region_group`
- `region`
- `city`
- `store_id`
- `store_name`
- `sales_person_id`
- `sales_person_name`
- `business_type`
- `order_status`
- `sales_amount`
- `gross_profit`
- `customer_id`
- `customer_type`
- `created_at`
- `updated_at`

关键规则：

- 默认业务日期字段固定使用 `statistics_date`
- 默认过滤固定包含 `order_status = 'completed'`
- 只有当用户明确要求创建时间视角时才应扩展到 `created_at`

## Metric Catalog

当前支持指标：

- `total_delivery_count`
- `car_sales_count`
- `rental_count`
- `used_car_count`
- `renewal_count`
- `sales_amount`
- `gross_profit`
- `average_order_value`

每个指标定义包含：

- `metric_id`
- 中文名 / 英文名
- 业务描述
- 表
- `time_field`
- 聚合逻辑
- 默认过滤
- 允许维度
- 公式
- owner
- 更新频率

## Mock 数据说明

系统会自动生成 24 个月以上的日粒度模拟订单，包含：

- 多渠道
- 多大区 / 区域 / 城市 / 门店
- 多销售人员
- 四类业务：`sale / rental / used_car / renewal`
- 工作日 / 周末效应
- 月度季节性
- 年度增长趋势
- 城市 / 渠道 / 门店差异
- 随机噪声

PostgreSQL 启动后：

1. `database/init.sql` 自动建表
2. `backend` 启动时调用与 `database/seed_data.py` 相同的生成逻辑
3. 若表为空则自动插入 mock 数据

## 运行方式

### 1. Docker 一键运行

```bash
docker compose up --build
```

访问地址：

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health API: `http://localhost:8000/api/health`

### 2. 本地开发运行

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

### 3. 手动重跑种子数据

```bash
python database/seed_data.py
```

## API 概览

- `GET /api/health`
- `GET /api/metrics/catalog`
- `GET /api/metrics/definition/{metric_id}`
- `POST /api/chat`
- `POST /api/metrics/query`
- `POST /api/metrics/explain`
- `POST /api/metrics/attribution`
- `POST /api/metrics/trend`
- `POST /api/metrics/ranking`

### `POST /api/chat` 示例

请求：

```json
{
  "session_id": "demo-session-001",
  "message": "最近7天趋势如何？"
}
```

澄清响应：

```json
{
  "type": "clarification",
  "message": "请问您想看哪个指标的趋势？",
  "options": ["总交车量", "卖车销量", "租车销量", "二手车销量", "续租量", "销售金额", "毛利"],
  "conversation_state": {}
}
```

## 支持的问题示例

- `今天交车多少？`
- `今天卖车同比多少？`
- `今天卖车环比多少？`
- `去年同期多少？`
- `上月同期多少？`
- `本月累计多少？`
- `最近7天卖车趋势如何？`
- `各城市卖车排名？`
- `各大区排名？`
- `按渠道拆解今天交车量`
- `按业务类型拆解今天交车量`
- `为什么今天卖车下降？`

## 测试

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm test
```

覆盖点包括：

- metric mapping
- time parsing
- clarification logic
- query plan generation
- SQL builder
- YOY / MOM / MTD
- ranking
- attribution
- API response schema

## 如何替换成企业真实数据库

1. 保持 `fact_delivery_orders` 或者创建一层同结构视图。
2. 将 `DATABASE_URL` 指向企业 PostgreSQL。
3. 把 `DEFAULT_DATA_SOURCE_LABEL` 改为 `real_database`。
4. 若真实库字段名不同，在 `metric catalog` 与 `sql_builder` 中统一映射。
5. 如需更多指标，在 `backend/app/metrics/catalog.json` 注册后，再扩展 NLU 映射和测试。

## 已知扩展方向

- 增加真实 LLM 作为 query-plan copilot，但继续保留 catalog 校验和 SQL builder 白名单。
- 增加用户权限、列级权限和维度访问控制。
- 增加更多复杂归因模型、分群分析和预警订阅。

