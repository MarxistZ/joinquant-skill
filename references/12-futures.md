# 12 — 期货策略

> 聚宽支持商品期货和金融期货（股指期货）。需初始化为 `futures` 类型账户。

## 初始化期货账户

默认账户只能买卖股票和基金。必须设置 `type='futures'`：

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash
    set_subportfolios([SubPortfolioConfig(cash=init_cash, type='futures')])
    run_daily(market_open, time='every_bar', reference_security='CU9999.XSGE')
```

---

## 合约代码规则

| 类型 | 格式 | 示例 | 说明 |
|---|---|---|---|
| 具体合约 | 品种+年月.交易所 | `RB1909.XSGE` | 可下单 |
| 主力连续 | 品种+9999.交易所 | `AG9999.XSGE` | **不可下单**，仅查行情 |
| 品种指数 | 品种+8888.交易所 | `AG8888.XSGE` | **不可下单**，仅查行情 |

---

## 主力连续合约

期货合约生存周期有限，到期后交割。系统根据持仓量对合约拼接，形成**主力连续合约**（品种+9999）。

**主力合约定义**：某合约持仓量连续 2 天为同品种最大（金融期货限最近两个合约中选取），且相对当前主力为远期合约，则切换为主力。不会在日内切换。

**不可直接对主力连续合约下单**，须用 `get_dominant_future` 获取具体合约。

---

## 品种指数

品种指数数据使用**前一天的持仓量加权平均**计算（品种+8888）。**不可对品种指数下单**。

---

## get_dominant_future 获取主力合约

```python
get_dominant_future(underlying_symbol, date=None)
```

- `underlying_symbol`: 品种代码，如 `'IF'`、`'AG'`
- `date`: 查询日期。回测中默认为回测日期；研究中默认为最新日期。

```python
get_dominant_future('IF')  # → 'IF1608.CCFX'
get_dominant_future('AG')  # → 'AG2106.XSGE'
```

## get_future_contracts 可交易合约列表

```python
get_future_contracts(security, date=None)
```

- `security`: 品种代码，如 `'AG'`
- `date`: 查询日期（同上）

```python
get_future_contracts('IF')
# ['IF1606.CCFX', 'IF1607.CCFX', 'IF1609.CCFX', 'IF1612.CCFX']
```

---

## 保证金设置

```python
set_option('futures_margin_rate', 0.25)            # 所有期货 25%
set_option('futures_margin_rate.AU1709', 0.08)     # AU1709 合约 8%
set_option('futures_margin_rate.AU', 0.09)          # 所有黄金期货 9%
set_option('futures_margin_rate', 0.1)             # 所有期货 10%
set_option('futures_margin_rate.IF', 0.15)          # 所有股指期货 15%
```

**保证金机制**：
- 非中金所品种：使用**合约单边保证金**，同一合约双向持仓只收最大那一边的保证金。
- 中金所股指期货：使用**跨品种单边保证金**，所有中金所品种只收双向持仓中更大的那一边。

**默认保证金比例**：股指期货 15%；商品期货按品种不同在 4%~20% 之间（如 AG 4%、BB 20%）。

### is_dangerous 保证金预警

```python
context.subportfolios[i].is_dangerous(margin_rate)
```

判断指定仓位的保证金比率是否低于 `margin_rate`。低于返回 `True`，高于返回 `False`。

```python
context.subportfolios[1].is_dangerous(0.2)
# 保证金低于 20% 返回 True
```

---

## 获取期货行情

`get_price`、`get_bars`、`history`、`attribute_history`、`get_current_data` 等 API 均可正常使用。新增 `open_interest`（持仓量）字段。

```python
df = get_price('C1909.XDCE', end_date='2019-06-28 15:00:00', count=5,
               fields=['close', 'open_interest'], frequency='1m')
print(df)
```

注意：`get_price` 中 `pre_close` 获取天数据时为**前结算价**。

---

## 期货下单函数

所有下单函数都增加 `side` 和 `close_today` 参数：

- `side`: `'long'`（多单）/ `'short'`（空单），**非买卖方向**。amount 正负决定开/平。
- `close_today`: 平今字段（详见下文）

### order 按手数下单

```python
order(security, amount, style=None, side='long', pindex=0, close_today=False)
```

```python
order('IF1412.CCFX', 1, side='short', pindex=0)    # 开空单
order('IF1412.CCFX', 1, side='long', pindex=0)     # 开多单
order('IF1412.CCFX', -1, side='long', pindex=1)    # 平多单
order('IF1412.CCFX', -1, LimitOrderStyle(3600.0), side='short', pindex=1)  # 限价平空
```

### order_target 目标手数下单

```python
order_target(security, amount, style=None, side='long', pindex=0, close_today=False)
```

使最终标的数量达到 `amount`，直接对目标方向操作。

```python
order_target('IF1412.CCFX', 5, side='long', pindex=1)   # 开 5 手多单
order_target('IF1412.CCFX', 4, side='long', pindex=1)   # 平 1 手多单
order_target('IF1412.CCFX', 5, side='short', pindex=1)  # 开 5 手空单
order_target('IF1412.CCFX', 4, side='short', pindex=1)  # 平 1 手空单
```

### order_value 按保证金下单

```python
order_value(security, value, style=None, side='long', pindex=0, close_today=False)
```

`value = 最新价 × 手数 × 保证金率 × 乘数`。

```python
order_value('IF1412.CCFX', 5000000, side='long', pindex=1)   # 开多
order_value('IF1412.CCFX', -4000000, side='long', pindex=1)  # 平多
```

### order_target_value 目标保证金下单

```python
order_target_value(security, value, style=None, side='long', pindex=0, close_today=False)
```

调整标的仓位到 `value` 保证金价值。

```python
order_target_value('IF1412.CCFX', 5000000, side='long', pindex=1)  # 调整至 5000000
order_target_value('IF1412.CCFX', 4000000, side='long', pindex=1)  # 调整至 4000000
order_target_value('IF1412.CCFX', 0, side='long', pindex=1)        # 全平
```

---

## close_today 平今参数

仅对以下交易所生效：上海国际能源中心、上海期货交易所、中金所。

| 值 | 行为 |
|---|---|
| `True` | 只平今仓 |
| `False`（默认） | 优先平昨仓，不足部分平今仓 |

其他交易所使用 `close_today` 会报错（按先开先平处理）。

---

## 期货注意事项

- 有夜盘的商品期货一个交易日从前一天 21:00 开始
- 每日 16:00 结算，使用结算价
- 持仓到交割日，系统自动以结算价平仓（无手续费、无交易记录）
- 股指期货平今手续费默认万分之六点九
- `get_price`、`get_bars`、`history` 等行情 API 新增 `open_interest`（持仓量）字段
- `pre_close` 在天数据中为前结算价
- 主力连续合约和品种指数**不可直接下单**

---

## 常见失败模式

❌ 在 `type='stock'` 账户中买期货 → 需要 `type='futures'`
❌ 对主力合约 `IF9999.CCFX` 直接下单 → 不可下单，用 `get_dominant_future` 获取具体合约
❌ 在非上期所/中金所品种上使用 `close_today=True` → 会报错
❌ 忘记设置 `reference_security` → `run_daily` 需要期货类型参考标的
❌ 混淆 `side='long'` 和正负 `amount` → amount 正=开仓/负=平仓，side 指多空方向
