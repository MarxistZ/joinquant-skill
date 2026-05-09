# 07 — 对象（核心 API 对象速查）

> 聚宽回测中的核心对象。理解属性含义是写策略的基础。

---

## `g`（全局变量）

**用途**：在模拟盘每次进程重启时持久化存储自定义变量。

```python
def initialize(context):
    g.security = "000001.XSHE"
    g.count = 1

def process_initialize(context):
    g.__q = query(valuation)   # __ 前缀 → 不会被 pickle 序列化

def handle_data(context, data):
    log.info(g.security)
```

- 模拟盘每天重启，g 中数据会被 pickle 保留；不用 g 则重启后丢失
- `__` 前缀的变量跳过序列化（适合放不可 pickle 的对象，如 SQLAlchemy query）
- 总大小上限 30MB，超限报错
- 不要在函数体外声明 g 变量（每次重启会重新执行初始化代码）

---

## `Context`（策略上下文）

**访问方式**：`handle_data(context, data)` 的第一个参数

```python
# 时间相关
year  = context.current_dt.year     # 当前 bar 时间
prev  = context.previous_date       # 前一交易日（datetime.date，不是 datetime）
dt    = context.current_dt          # datetime.datetime

# 账户
p     = context.portfolio           # Portfolio 总账户
subs  = context.subportfolios       # list[SubPortfolio]

# 股票池
pool  = context.universe            # set_universe() 设定的池

# 运行参数
params = context.run_params
print(params.start_date, params.end_date)   # datetime.date
print(params.type)                          # 'simple_backtest' / 'full_backtest' / 'sim_trade'
print(params.frequency)                     # 'day' / 'minute' / 'tick'
```

**关键属性**：

| 属性 | 类型 | 说明 |
|---|---|---|
| `portfolio` | Portfolio | 总账户信息 |
| `subportfolios` | list[SubPortfolio] | 子组合列表 |
| `current_dt` | datetime.datetime | 当前 bar 开始时间 |
| `previous_date` | datetime.date | 前一交易日（date 类型） |
| `universe` | list[str] | 设定的股票池 |
| `run_params` | RunParameters | 运行参数（见上方） |

**注意**：context 也能像 g 一样持久化用户变量（`__` 前缀跳过），但更推荐用 g。不要持久化 context 下的 order/trade/position 等可变对象。

---

## `Portfolio`（总账户）

**访问方式**：`context.portfolio`

```python
p = context.portfolio
print(p.available_cash)      # 可用资金（下单用）
print(p.total_value)         # 总权益（现金 + 持仓市值）
print(p.locked_cash)         # 挂单冻结资金
print(p.positions)           # dict[str, Position] = long_positions
print(p.long_positions)      # 多头持仓
print(p.short_positions)     # 空头持仓
print(p.starting_cash)       # 初始资金（= inout_cash）
print(p.inout_cash)          # 累计出入金（含初始）
print(p.transferable_cash)   # 可取资金（不含今日卖出所得）
print(p.positions_value)     # 持仓价值
print(p.margin)              # 保证金
print(p.returns)             # 累计收益率
```

**属性全表**：

| 属性 | 说明 |
|---|---|
| `inout_cash` | 累计出入金（含初始资金） |
| `available_cash` | 可用资金 |
| `transferable_cash` | 可取资金（今日卖出所得不可取） |
| `locked_cash` | 挂单冻结资金 |
| `margin` | 保证金（股票=100%，期货实时更新） |
| `positions` | = `long_positions`（dict[code, Position]） |
| `long_positions` | 多头持仓 |
| `short_positions` | 空头持仓 |
| `total_value` | 总权益 |
| `returns` | 前一日总权益的累计收益 |
| `starting_cash` | = `inout_cash`，初始资金 |
| `positions_value` | 持仓价值 |

**已过时**：`cash`（用 `available_cash`）、`portfolio_value`（用 `total_value`）、`unsell_positions`

---

## `SubPortfolio`（子组合）

**访问方式**：`context.subportfolios[i]`

默认单仓位时 `portfolio` 指向 `subportfolios[0]`。

| 属性 | 说明 |
|---|---|
| `inout_cash` | 累计出入金 |
| `available_cash` | 可用资金 |
| `transferable_cash` | 可取资金 |
| `locked_cash` | 挂单冻结资金 |
| `type` | 账户类型（'stock' / 'index_futures' 等） |
| `long_positions` | dict[code, Position] 多头持仓 |
| `short_positions` | dict[code, Position] 空头持仓 |
| `positions_value` | 持仓价值 |
| `total_value` | 总资产（现金 + 持仓/保证金） |
| `total_liability` | 总负债（融资融券） |
| `net_value` | 净资产 = total_value - total_liability |
| `cash_liability` | 融资负债 |
| `sec_liability` | 融券负债 |
| `interest` | 利息总负债 |
| `maintenance_margin_rate` | 维持担保比例 |
| `available_margin` | 两融可用保证金 |
| `margin` | 保证金 |

**SubPortfolioConfig 设置**：
```python
set_subportfolios([
    SubPortfolioConfig(cash=500000, type='stock'),
    SubPortfolioConfig(cash=500000, type='index_futures'),
])
```
下单时 `pindex=` 指定子组合。详见 `references/09-multi-portfolio.md`。

---

## `Position`（持仓）

**访问方式**：`context.portfolio.positions.get(security)` 或 `context.subportfolios[i].long_positions[security]`

```python
pos = context.portfolio.positions.get('000001.XSHE')
if pos is not None and pos.total_amount > 0:
    print(pos.security)          # 标的代码
    print(pos.total_amount)      # 总持仓（不含挂单冻结！）
    print(pos.closeable_amount)  # 可平仓数量（A 股 T+1）
    print(pos.locked_amount)     # 挂单冻结数量
    print(pos.today_amount)      # 今日开仓数量
    print(pos.avg_cost)          # 当前持仓成本（加仓更新，减仓不变）
    print(pos.acc_avg_cost)      # 累计持仓成本（加减仓都更新）
    print(pos.hold_cost)         # 当日持仓成本（清算后=前收价）
    print(pos.price)             # 最新行情价
    print(pos.value)             # 标的价值 = price * total_amount * multiplier
    print(pos.side)              # 'long' / 'short'
    print(pos.pindex)            # 子组合索引
    print(pos.init_time)         # 首次建仓时间
    print(pos.transact_time)     # 最后交易时间
```

**关键理解**：

| 概念 | 说明 |
|---|---|
| `total_amount` | **不包含** `locked_amount`。实际持仓 = `total_amount + locked_amount` |
| `closeable_amount` | 可卖数量（A 股 T+1，今日买的不可卖） |
| `today_amount` | 今日开仓数量 |
| `locked_amount` | 挂单冻结数量 |
| `avg_cost` | 加仓更新，减仓不变（用于算浮动盈亏） |
| `acc_avg_cost` | 加减仓都更新（含累计盈亏） |
| `hold_cost` | 当日无收益则 = 前收盘价（清算后） |
| `value` | = `price * total_amount * multiplier`（股票、基金 multiplier=1，期货=合约乘数） |

**已过时**：`sellable_amount` / `amount`（二者都 = `closeable_amount`）

---

## `Order`（订单）

**返回方式**：所有下单函数（`order` / `order_value` 等）的返回值

```python
o = order_value('000001.XSHE', 50000)
if o is not None:
    print(o.order_id)            # 订单 ID
    print(o.security)            # 标的
    print(o.amount)              # 委托数量（正数）
    print(o.filled)              # 已成交数量
    print(o.price)               # 成交均价（已成交部分的均价）
    print(o.avg_cost)            # 卖出：卖出前持仓成本；买入 = price
    print(o.status)              # OrderStatus 枚举
    print(o.side)                # 'long' / 'short'
    print(o.action)              # 'open' / 'close'
    print(o.is_buy)              # bool 是否买入
    print(o.add_time)            # 委托时间 datetime.datetime
    print(o.commission)          # 交易费用
```

`price` vs `avg_cost`：卖出时 `avg_cost` 是下单前的持仓成本（用于算卖出收益），买入时 `avg_cost` = `price`。

**注意**：不要在策略中跨交易日保存当天的 Order 对象。

---

## `OrderStatus`（订单状态枚举）

| 枚举值 | 整数值 | 含义 |
|---|---|---|
| `new` | 8 | 已创建未委托（盘前/隔夜单，开盘变 open） |
| `open` | 0 | 已报待成交 |
| `filled` | 1 | **部分成交**（未完成） |
| `held` | 4 | **全部成交**（已完成） |
| `canceled` | 2 | 已撤销（可能有部分成交，看 `filled` 字段） |
| `rejected` | 3 | 被拒（可能有部分成交） |

**⚠️ 极易混淆**：`filled` = 部分成交，`held` = 全部成交（命名反直觉）。

比较方式：`str(order.status) == 'held'`

---

## `OrderStyle`（下单类型）

### `MarketOrderStyle(limit_price=None)` 

市价单。`limit_price` 仅对科创板生效（保护价）。

```python
order('000001.XSHE', 100, MarketOrderStyle())           # 市价单
order('688003.XSHG', 200, MarketOrderStyle(200))        # 科创板保护价 200
```

### `LimitOrderStyle(limit_price)` 

限价单。

```python
order('000001.XSHE', 100, LimitOrderStyle(15.0))
order('IF1412.CCFX', -1, LimitOrderStyle(3600.0), side='short', pindex=1)
```

### 停止单

```python
StopMarketOrderStyle(mode, stop_price)
StopLimitOrderStyle(mode, stop_price, limit_price)
```

| 参数 | 说明 |
|---|---|
| `mode` | `'stop_loss'`（止损）或 `'take_profit'`（止盈） |
| `stop_price` | 触发价，突破后转为市价/限价单 |
| `limit_price` | 限价（仅 StopLimitOrderStyle） |

- 触发价不满足条件时立即触发
- 不会提前锁定持仓/资金，触发时条件不足则失败
- 当天未完成的停止单盘后撤销
- `order_value` / `order_target_value` 用停止单时：实际委托数量 = value / 价格 / 保证金率 / 乘数

---

## `Trade`（成交记录）

**获取方式**：`get_trades()` 返回 dict

```python
trades = get_trades()
for t in trades.values():
    print(t.time)       # 成交时间 datetime.datetime
    print(t.security)   # 标的代码
    print(t.amount)     # 成交数量
    print(t.price)      # 成交价格
    print(t.trade_id)   # 成交记录 ID
    print(t.order_id)   # 对应订单 ID
```

一个订单可能分多次成交（部分成交场景）。

---

## `Tick`（快照数据）

**访问方式**：tick 频率回测或 `get_current_tick()`

| 属性 | 说明 |
|---|---|
| `code` | 标的代码 |
| `datetime` | tick 时间 |
| `current` | 最新价 |
| `open` | 当日开盘价 |
| `high` / `low` | 截至当前最高价 / 最低价 |
| `volume` | 截至当前成交量 |
| `money` | 截至当前成交额 |
| `position` | 持仓量（仅期货） |
| `a1_p` ~ `a5_p` | 卖一价 ~ 卖五价 |
| `a1_v` ~ `a5_v` | 卖一量 ~ 卖五量 |
| `b1_p` ~ `b5_p` | 买一价 ~ 买五价 |
| `b1_v` ~ `b5_v` | 买一量 ~ 买五量 |

**期货仅一档**（a1/b1），**沪深股票五档**（a1~a5 / b1~b5）。

---

## `SecurityUnitData`（单标的 bar 数据）

`data[security]` 或 `attribute_history()` / `get_price()` 返回的 DataFrame 元素。

| 属性/方法 | 说明 |
|---|---|
| `open` / `close` / `high` / `low` | OHLC 价 |
| `volume` | 成交量 |
| `money` | 成交额 |
| `factor` | 前复权因子（原始价 = close / factor） |
| `high_limit` | 涨停价 |
| `low_limit` | 跌停价 |
| `avg` | 时段均价 |
| `pre_close` | 前收盘价（分钟频率下 = open；期货是前前日结算价） |
| `paused` | bool，是否停牌（OHLC 有值 = 停牌前收盘，volume/money = 0） |
| `security` | 标的代码 |
| `returns` | = (close - pre_close) / pre_close |
| `isnan()` | 数据是否无效（未上市或退市） |
| `mavg(days, field='close')` | N 期均线，默认收盘价 |
| `vwap(days)` | N 期 VWAP |
| `stddev(days)` | N 期标准差 |

`price` 已过时 = `avg`。mavg/vwap/stddev 跳过停牌日，交易日不足返回 NaN。

---

## `OrderCost`（交易费用）

```python
set_order_cost(OrderCost(
    open_tax=0,                   # 买入印花税（A 股 = 0）
    close_tax=0.001,              # 卖出印花税（0.1%）
    open_commission=0.0003,       # 买入手续费（万 3）
    close_commission=0.0003,      # 卖出手续费（万 3）
    close_today_commission=0,     # 平今手续费
    min_commission=5,             # 最低手续费（5 元）
), type='stock')
```

`type`：`'stock'` / `'fund'` / `'mmf'` / `'index_futures'` / `'futures'` / `'options'` / `'bond_fund'` / `'stock_fund'`

---

## `Slippage`（滑点）

| 类型 | 说明 | 示例 |
|---|---|---|
| `FixedSlippage(value)` | 固定滑点（元/股） | `set_slippage(FixedSlippage(0.02))` |
| `PriceRelatedSlippage(value)` | 比例滑点 | `set_slippage(PriceRelatedSlippage(0.00246))` |
| `StepRelatedSlippage(value)` | 最小变动单位（期货） | `set_slippage(StepRelatedSlippage(2))` |

---

## 事件对象

### `DividendsEvent` — 分红送股

| 属性 | 说明 |
|---|---|
| `name` | `'Dividends'` |
| `pindex` | 子账户索引 |
| `security` | 标的代码 |
| `side` | `'long'` / `'short'` |
| `dividends` | dict list，key: `date` / `scale_factor` / `bonus_pre_tax` / `bonus_post_tax` |

### `ForcedLiquidationEvent` — 强行平仓

| 属性 | 说明 |
|---|---|
| `name` | `'ForcedLiquidation'` |
| `pindex` | 子账户索引 |
| `security` | 标的 |
| `side` | `'long'` / `'short'` |
| `amount` | 强平数量 |

---

## 必背规则

1. **判断持仓用 `total_amount > 0`**，不要用 `if pos`
2. **`total_amount` 不包含 `locked_amount`**，实际持仓 = `total_amount + locked_amount`
3. **可卖用 `closeable_amount`** — A 股 T+1
4. **`filled` = 部分成交，`held` = 全部成交** — 反直觉但必须牢记
5. **Order 可能为 None** — 下单失败时
6. **手续费 type 要选对** — `'stock'` 与 `'index_futures'` 算法完全不同
7. **限价单会一直挂** — 记得 `cancel_order` 清理过期订单
8. **停止单当天有效** — 未成交盘后撤销，不提前锁定资金

---

## AI 常编错的属性

| AI 编的 | 实际应该用 |
|---|---|
| `position.amount` | `position.total_amount`（或 `closeable_amount`） |
| `position.cost_price` | `position.avg_cost` |
| `position.market_value` | `position.value` |
| `portfolio.cash_balance` | `portfolio.available_cash` |
| `portfolio.holdings` | `portfolio.positions` |
| `portfolio.cash` | `portfolio.available_cash`（`cash` 已过时） |
| `order.id` | `order.order_id` |
| `order.quantity` | `order.amount` |
| `order.filled_quantity` | `order.filled` |
| `order.status == 'filled'` 表示全成交 | `'held'` 才是全成交，`'filled'` 是部分 |
