# 01 — 策略设置函数

> 这是聚宽策略代码的"骨架"。每个策略都必须实现 `initialize`，并在里面调用必备的 set 系列函数。

## 必须实现的策略入口函数

### `initialize(context)` ★

**调用时机**：策略启动时（回测/模拟/实盘）只调用一次。

**职责**：
- 设置基准、复权模式、税费、滑点
- 初始化全局变量（用 `g.xxx`）
- 注册定时任务（`run_daily` / `run_weekly` / `run_monthly`）

**示例**：
```python
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(FixedSlippage(0.02))
    g.security = '000001.XSHE'
    run_daily(trade, time='open')
```

### `before_trading_start(context)`

**调用时机**：每个交易日开盘前 09:00 前（官方文档说明启动时间为'0900'）。
**用途**：选股、设置今日目标。
**注意**：**禁止下单**。下单必须放到 `handle_data` 或 `run_daily` 调度的函数。

### `handle_data(context, data)`

**调用时机**：分钟回测每分钟、日回测每日。
**注意**：现在更推荐用 `run_daily(func, time=...)` 替代直接写 `handle_data`。

### `after_trading_end(context)`

**调用时机**：每个交易日收盘后 15:30 之后。
**用途**：日终统计、打印日志。
**注意**：**禁止下单**。

### `process_initialize(context)`

**调用时机**：每次回测/模拟进程重启时执行。在 `initialize` 之后执行。
**用途**：初始化不能持久化保存的内容（如 `query` 对象等不支持 pickle 序列化的内容）。

```python
def process_initialize(context):
    # query 对象不能持久保存，每次进程重启重新初始化
    g.__q = query(valuation)
```

### `after_code_changed(context)`

**调用时机**：模拟盘恢复时检测到代码已修改，则在恢复时执行此函数。在 `process_initialize` 之前执行。
**用途**：修改模拟盘数据、取消旧定时任务并注册新任务。

```python
def after_code_changed(context):
    unschedule_all()
    run_daily(func, '10:00')
```

### `on_event(context, event)`

**调用时机**：账户持仓标的触发特定事件时调用。建议用 `isinstance` 判断事件类型。
**支持的事件**：
- `DividendsEvent`：分红送股事件
- `ForcedLiquidationEvent`：强行平仓事件

```python
def on_event(context, event):
    if isinstance(event, DividendsEvent):
        log.info('分红送股事件')
```

### `on_strategy_end(context)`

**调用时机**：回测/模拟交易正常结束时调用（失败时不会被调用）。
**用途**：收尾清理、结果汇总。

```python
def on_strategy_end(context):
    log.info('策略运行结束')
```

---

## 配置类函数（在 `initialize` 里调用）

### `set_benchmark(security)` ★

设置基准指数。不设置时默认使用沪深 300 指数（`000300.XSHG`）。

**参数**：
- `security`：股票/指数/ETF 代码（字符串），或一个 dict。dict 的 key 为代码，value 为权重（小于 1 的浮点数），权重之和必须 ≤ 1（小于 1 代表基准中部分资金闲置）。

**示例**：
```python
# 简单基准——沪深300
set_benchmark('000300.XSHG')

# 自定义组合基准（多标的加权）
set_benchmark({'000001.XSHG': 0.5, '000300.XSHG': 0.3, '600000.XSHG': 0.2})

# 期货策略中不显示基准线（但无法计算 alpha 等收益）
set_benchmark({"000001.XSHG": 0})
```

### `set_order_cost(cost, type, ref)` ★

设置佣金/印花税等交易费用。

**签名**：
```python
set_order_cost(cost, type, ref=None)
```

**`OrderCost` 对象字段**：
| 字段 | 含义 | 适用说明 |
|---|---|---|
| `open_tax` | 买入印花税 | 仅股票类收取，基金/期货为 0 |
| `close_tax` | 卖出印花税 | 仅股票类收取，基金/期货为 0 |
| `open_commission` | 买入佣金 | 全部类型适用 |
| `close_commission` | 卖出佣金 | 全部类型适用 |
| `close_today_commission` | 平今仓佣金 | 期货专用，股票设为 0 |
| `min_commission` | 最低佣金 | 不含印花税；股票通常 5 元，期货通常 0 |

**`type` 可选值**：
`'stock'` / `'fund'` / `'mmf'` / `'fja'` / `'fjb'` / `'fjm'` / `'index_futures'` / `'futures'`（含股指和商品期货） / `'bond_fund'` / `'stock_fund'` / `'QDII_fund'` / `'mixture_fund'`

**`ref`**：参考代码，用于给特定标的单独设置费率。如 `'000001.XSHE'`、`'IF1709'`、`'IF'`、`'AU'`。为特定标的设置时必须同时指定 `type` 为对应交易品种类别。

**示例**：
```python
# A 股默认费率（买入万3，卖出万3+千1印花税，最低5元）
set_order_cost(OrderCost(open_tax=0, close_tax=0.001,
                         open_commission=0.0003, close_commission=0.0003,
                         close_today_commission=0, min_commission=5),
               type='stock')

# 股指期货（平今仓佣金较高）
set_order_cost(OrderCost(open_tax=0, close_tax=0,
                         open_commission=0.000023, close_commission=0.000023,
                         close_today_commission=0.0023, min_commission=0),
               type='index_futures')

# 单独设置某只股票
set_order_cost(OrderCost(...), type='stock', ref='000300.XSHG')

# 设置所有期货品种（含股指期货和商品期货）
set_order_cost(OrderCost(...), type='futures')

# 单独设置 AU 品种
set_order_cost(OrderCost(...), type='futures', ref='AU')
```

> ⚠️ **AI 常编错**：`type` 是必填参数，建议写为关键字形式 `type='stock'`。`min_commission=5` 只对股票有效，期货应设为 0。期货合约持仓到交割日会以当天结算价平仓，无手续费，无交易记录。给特定标的设置费率时必须同时指定 `type`（不能只传 `ref` 不传 `type`）。

### `set_slippage(object, type, ref)` ★

设定滑点，模拟真实市场成交价差。

**签名**：
```python
set_slippage(object, type=None, ref=None)
```

**参数**：
- `object`：滑点对象，支持三种类型（见下）
- `type`：交易品种，`'stock'` / `'fund'` / `'index_futures'`（金融期货）/ `'futures'`（含股指和商品期货）/ `'bond_fund'` / `'stock_fund'` / `'QDII_fund'` / `'money_market_fund'` / `'mixture_fund'`。为 `None` 时应用于全局。
- `ref`：标的代码。为特定标的单独设置时需同时指定 `type`。

**三种滑点类型**：
```python
# 1. 固定值滑点——加减固定金额（元）
set_slippage(FixedSlippage(0.02))
# 买单成交价 = 均价 + 0.01，卖单成交价 = 均价 - 0.01

# 2. 百分比滑点——按价格比例加减
set_slippage(PriceRelatedSlippage(0.002))
# 买单成交价 = 均价 + 0.1%，卖单成交价 = 均价 - 0.1%

# 3. 跳数滑点——期货专用，按合约最小变动单位（双边）
set_slippage(StepRelatedSlippage(2), type='futures', ref='CU')
# StepRelatedSlippage(2) 表示单边滑点为 1 个价格最小变动单位
# 开多仓: 现价 + 1 跳，开空仓: 现价 - 1 跳
```

**默认值**：不调用 `set_slippage` 时，系统使用 `PriceRelatedSlippage(0.00246)`。

> ⚠️ **重要**：`'mmf'`（货基）与 `'money_market_fund'` 类型标的滑点固定为 0，调用 `set_slippage` 重新设置也不会生效。

### `set_option(option, value)` ★

通用选项设置函数。以下是各关键选项详解。

---

#### `set_option('use_real_price', value)` — 动态复权模式

**强烈建议开启**。默认 `False`（保持旧策略兼容）。

**开启（`True`）后的行为**：
- 每天看到的当天价格是真实的（不复权）
- 使用真实价格下单，交易/持仓详情显示真实价格
- 数据获取 API（`attribute_history`、`get_price` 等）返回的是 **基于当天日期的前复权价格**
- 持仓发生送股/分红时，股数和现金自动调整

```python
set_option('use_real_price', True)
```

> ⚠️ **use_real_price 的陷阱**：
> - **不要跨日期缓存数据获取函数的结果**——不同日期的前复权价格不同
> - 买入数量必须是 100 的倍数，开启前后回测结果可能不同
> - 对 **期货不生效**
> - **不建议给含场内基金的策略开启**——场内基金除权日披露不标准
> - 如需获取昨天的真实价格，需手动反算：
>   ```python
>   df = attribute_history(s, 1, '1d', fields=['close', 'factor'])
>   real_close = df['close'][-1] / df['factor'][-1]
>   ```

---

#### `set_option('avoid_future_data', value)` — 避免未来数据

**默认 `False`（关闭）**。开启后帮助发现回测中引入未来数据的问题。

`True` 时的行为：
- 通过 API 获取 `current_dt` 之后的数据 → 抛出 `FutureDataError`
- 无法通过时间参数规避的未来数据（如 `get_call_auction`）→ 自动剔除未来部分

```python
set_option('avoid_future_data', True)
```

> ⚠️ **AI 常编错**：此选项默认是 **False**，不是 True。此外该选项不是万能的——外部数据、固定股票池中设历史大牛股等引入的未来数据无法检测。

---

#### `set_option('order_volume_ratio', value)` — 成交量比例

限制每笔订单的成交量。**默认 `1.0`**（无限制）。

- 市价单：成交量 ≤ 当日总成交量 × value
- 限价单：分价表中每个价格的成交量按 value 比率匹配

```python
# 每笔订单不超过当日成交量的 25%
set_option('order_volume_ratio', 0.25)
```

> 注意：当下单量超过全市场所有成交量时，系统直接取全市场成交量。

---

#### `set_option('match_with_order_book', value)` — 盘口撮合

**只对模拟盘生效**。默认 `False`（使用 Bar 撮合）。

```python
# 开启盘口撮合，更接近真实交易
set_option('match_with_order_book', True)
```

### `disable_cache()`

关闭系统缓存。当策略内存占用过大、频繁触发 OOM 被杀时，可在 `initialize` 中调用。会降低运行速度。

```python
disable_cache()
```

### `set_universe(securities)`

旧 API。现在仅用于设定 `history` 函数的默认股票池 `context.universe`，除此之外无其他用途。建议在 `before_trading_start` 中动态选股。

### `set_commission(object)` [已废弃]

已废弃，请使用 `set_order_cost` 替代。不要在新策略中使用。

旧签名：`set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))`

---

## 实验性设置项

以下非常规实验设置在特殊研究需求时使用：

```python
# T+0 模式：A 股买入后可以立刻卖出
set_option("t0_mode", True)

# 总是撮合市价单：支持在非交易时间下市价单，按最新数据立即撮合
set_option("always_match_market_order", True)

# 强制撮合（仅支持限价单）：限价单不检查价格和数量直接成交；市价单的成交价不受滑点影响
set_option("match_by_signal", True)
```

---

## 调度函数

### `run_daily(func, time='9:30', reference_security)` ★

按天定时运行指定函数。`run_daily` 没有 `force` 属性。

**`time` 支持三种格式**：
1. 具体时间：`"10:00"`, `"14:50"` 等在 24 小时内
2. `"every_bar"`：仅在 `run_daily` 可用。按天回测每天开盘执行一次，按分钟回测每分钟执行（tick 不支持）
3. `"open"` / `"open+5m"` / `"open-10m"`：参照 `reference_security` 的开盘时间（±X 分钟），一般用于期货

**`reference_security`**：时间参照标的代码，默认为 `'000001.XSHG'`（股票交易时间 09:30~15:00）。如参照 `'IF9999.CCFX'` 则以期货时间为准。期货策略建议修改为对应的主力合约。当 `time` 为具体时间时请勿设置此参数。

```python
run_daily(market_open, time='open')              # 参照标的开盘时运行（股票为 09:30）
run_daily(market_close, time='14:50')            # 尾盘 14:50
run_daily(intraday, time='every_bar')            # 每根 bar
run_daily(custom, time='10:00')                  # 自定义时间
# 期货以主力合约为参照，开盘前 10 分钟运行
run_daily(before_open, time='open-10m', reference_security='IF9999.CCFX')
```

### `run_weekly(func, weekday, time='9:30', reference_security, force=False)`

```python
run_weekly(rebalance, weekday=1, time='09:31')  # 每周第 1 个交易日 09:31
```

- `weekday`：每周第几个交易日，支持负数（倒数）。如 `weekday=1` 为第一个交易日。
- `reference_security`：时间参照标的代码，默认为 `'000001.XSHG'`。
- `force`：若注册回调函数的时间晚于第一次回调的执行时间，是否就近执行，默认为 `True`，建议设为 `False`。

### `run_monthly(func, monthday, time='9:30', reference_security, force=False)`

```python
run_monthly(rebalance, monthday=1, time='09:31')  # 每月第 1 个交易日
```

- `monthday`：每月第几个交易日，支持负数（倒数）。`monthday=-1` 为每月最后一个交易日。
- `reference_security`：时间参照标的代码，默认为 `'000001.XSHG'`。
- `force`：若注册回调函数的时间晚于第一次回调的执行时间，是否就近执行，默认为 `True`，建议设为 `False`。

### `unschedule_all()`

取消所有已注册的定时任务。常用于 `after_code_changed` 中重新注册任务。

```python
unschedule_all()
```

---

## 多投资组合（高级）

```python
set_subportfolios([
    SubPortfolioConfig(cash=500000, type='stock'),
    SubPortfolioConfig(cash=500000, type='index_futures'),
])
```

详见 `references/09-multi-portfolio.md`。

---

## 期货 / 融资融券额外设置

参见对应专门文档：
- `references/12-futures.md`
- `references/11-margin-trading.md`

---

## 检查清单（lint 工具会查）

| 项 | 必要程度 | 不设的后果 |
|---|---|---|
| `set_benchmark` | 建议 | 默认沪深 300；追踪其他指数时必须要显式设置 |
| `set_option('use_real_price', True)` | ✅ 必填 | 回测有未来函数偏差，价格不真实 |
| `set_order_cost(...)` | ✅ 必填 | 用聚宽默认费率，与实际券商可能差很远 |
| `set_slippage(...)` | ✅ 必填 | 回测无滑点，过于乐观 |

下单类函数禁止出现在：
- `before_trading_start`
- `after_trading_end`
- 全局作用域（必须在函数里）

---

## 常见失败模式

❌ `set_initial_cash(...)` —— 不存在的 API。初始资金在聚宽 Web 界面设置  
❌ 没有 `set_benchmark` —— 默认沪深 300；但不是你要的基准时策略对比无效  
❌ `set_option('avoid_future_data', True)` 以为默认开启 —— 实际默认是 **False**，需显式开启  
❌ `set_universe(['000001.XSHE'])` 然后期望它自动随时间变化 —— 它不会，得在 `before_trading_start` 动态算  
❌ `run_daily(func)` 没传 `time` —— 默认 `'9:30'`（09:30），可能不是你想要的  
❌ `set_order_cost(OrderCost(...), 'stock')` 只传位置参数 —— 建议写 `type='stock'` 更清晰  
❌ 开启 `use_real_price` 后跨日期缓存 `attribute_history` 的结果 —— 前复权价格每天不同  
❌ `set_order_cost` 中 `min_commission=5` 照搬到期货 —— 期货最低佣金应为 0  
❌ 认为 `set_commission` 仍然可用 —— 已废弃，必须用 `set_order_cost`
