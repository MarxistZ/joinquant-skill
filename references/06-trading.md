# 06 — 交易函数

> 所有"下单/撤单/查订单/出入金"相关 API。**必须在交易时间调用**——禁止在 `before_trading_start` / `after_trading_end` 中下单。
> 可在 `handle_data` 或定时运行函数（`time='every_bar'` 或具体时间如 `'10:00'`）中使用。

## 主下单函数

### `order(security, amount, style=None, side='long', pindex=0, close_today=False)` ★

按股数下单。

```python
order('000001.XSHE', 1000)           # 买入 1000 股
order('000001.XSHE', -1000)          # 卖出 1000 股
order('000001.XSHE', 1000, LimitOrderStyle(15.0))  # 限价单
order('688001.XSHG', 100, MarketOrderStyle(10))    # 科创板指定保护价
```

**返回**：`Order` 对象 / `None`（失败）

**注意**：amount 须为 100 整数倍（A 股一手），卖光所有股票时不受限制。科创板起购 200 股。

### `order_value(security, value, style=None, side='long', pindex=0, close_today=False)` ★

按价值下单（**推荐**）。

```python
order_value('000001.XSHE', 50000)    # 买入 50000 元
order_value('000001.XSHE', -30000)   # 卖出 30000 元
```

**自动处理**：按当前价计算股数，向下取整到 100 整数倍。

### `order_target(security, amount, style=None, side='long', pindex=0, close_today=False)` ★

调整目标持仓数量。

```python
order_target('000001.XSHE', 0)       # 清仓
order_target('000001.XSHE', 1000)    # 调到 1000 股
```

**注意**：若该标的有未完成订单，会自动取消再下单。

### `order_target_value(security, value, style=None, side='long', pindex=0, close_today=False)` ★

调整目标持仓**价值**。

```python
order_target_value('000001.XSHE', 50000)  # 调到 50000 元
order_target_value('000001.XSHE', 0)      # 清仓
```

**注意**：若该标的有未完成订单，会自动取消再下单。

### `order_market(security, amount, side='long', pindex=0)`

市价单。等价于 `order(security, amount)`。

**注意**：此函数未在官方 API 文档中出现，可能为旧版本函数或未记录函数，请谨慎使用。

### `order_lots(security, lots, style=None, ...)`

按手数下单（1 手 = 100 股）。`order_lots('000001.XSHE', 10)` 买 10 手。

**注意**：此函数未在官方 API 文档中出现，可能为旧版本函数或未记录函数，请谨慎使用。

---

## 订单查询 / 取消

### `get_open_orders()`

查询当日未完成订单。返回 dict（key=order_id, value=Order）。

```python
open_orders = get_open_orders()
for o in open_orders.values():
    print(o.order_id, o.security, o.amount, o.status)
```

### `get_orders(order_id=None, security=None, status=None)`

查询当日所有订单（含已完成）。status 用 `OrderStatus` 枚举。

```python
get_orders()                                    # 全部
get_orders(order_id='1517627499')               # 按 ID
get_orders(security='000002.XSHE')              # 按标的
get_orders(status=OrderStatus.held)             # 按状态
```

**注意**：非交易时间下单状态为 `new`（已创建未委托），开盘后变为 `open`（已委托未完成）。

### `get_trades()`

查询当日成交记录。一个订单可能分多次成交。

### `cancel_order(order)`

取消订单。可传 `order_id` 字符串或 `Order` 对象。

```python
for o in get_open_orders().values():
    if o.security == '000001.XSHE':
        cancel_order(o)
```

---

## close_today 参数（期货平今）

仅对 **上海国际能源中心、上期所、中金所** 生效：

| 值 | 行为 |
|---|---|
| `True` | 只平今仓，今仓不足时废单 |
| `False`（默认） | 优先平昨仓，昨仓不足平今仓 |

无论 True/False 只产生一笔订单，手续费率不同（平昨/平今费率）。**其他交易所将会报错**（不区分平今平昨，均先开先平）。注意：`batch_submit_orders` 在其他交易所上的 close_today 行为不同，见下方说明。

## 期货专用

| 函数 | 说明 |
|---|---|
| `buy_open(security, amount, ...)` | 期货开多 |
| `sell_open(security, amount, ...)` | 期货开空 |
| `buy_close(security, amount, ..., close_today=False)` | 期货平多 |
| `sell_close(security, amount, ..., close_today=False)` | 期货平空 |

详见 `references/12-futures.md`。

## 融资融券专用

| 函数 | 说明 |
|---|---|
| `margincash_open(security, amount, ...)` | 融资买入 |
| `margincash_close(security, amount, ...)` | 卖券还款 |
| `margincash_direct_refund(value, pindex=0)` | 直接还款 |
| `marginsec_open(security, amount, ...)` | 融券卖出 |
| `marginsec_close(security, amount, ...)` | 买券还券 |

详见 `references/11-margin-trading.md`。

---

## 篮子下单/撤单

### `batch_submit_orders(orders)` ★

批量委托。任一验资验券失败则整批失败。

```python
orders = [
    {"security": "000001.XSHE", "amount": 100},
    {"security": "600660.XSHG", "amount": 100},
]
batch_submit_orders(orders)
```

每个 dict 支持：security, amount, style, side（默认 'long'）, pindex（默认 0）, close_today。

**close_today 注意**：对其他交易所标的，True=优先平今(超出平昨)，False=优先平昨(超出平今)。

### `batch_cancel_orders(orders)` ★

批量撤单。orders 为列表，元素为 Order 对象或 order_id。

---

## 账户出入金

### `inout_cash(cash, pindex=0)` ★

账户转入/转出资金。正为入金，负为出金。当日计入本金影响收益。

```python
inout_cash(6666, pindex=0)   # 入金
inout_cash(-5000, pindex=0)  # 出金
```

---

## OrderStyle（订单类型）

- **`MarketOrderStyle(limit_price=None)`**：市价单（默认）。科创板必须指定保护价。
- **`LimitOrderStyle(limit_price)`**：限价单。

```python
order('000001.XSHE', 1000, MarketOrderStyle())
order('688001.XSHG', 100, MarketOrderStyle(10))   # 科创板保护价
order('000001.XSHE', 1000, LimitOrderStyle(15.0))
```

详见 `references/07-objects.md`。

---

## 撮合规则要点

- **市价单**：按最新价 + 滑点撮合
- **限价单**：下单时按最新价撮合，剩余挂单，每分钟 bar 结束时再撮合
- **涨停**：市价买单撤销；**跌停**：市价卖单撤销
- **交易日结束**：所有未完成订单自动取消

详见 `references/14-strategy-engine.md`。

---

## 多投资组合下单

用 `set_subportfolios([...])` 后，下单指定 `pindex`：

```python
order('000001.XSHE', 1000, pindex=0)   # 第一个 sub-portfolio
order('IF2306.CCFX', 1, pindex=1)      # 第二个 sub-portfolio
```

详见 `references/09-multi-portfolio.md`。

---

## 订单失败常见原因

`order()` 返回 `None` 的可能原因：股票停牌；标的代码错误/已退市/未上市；pindex 错误（如给股票下单指定期货账户）；调整后手数为 0；股票/基金开空单（不支持）；科创板市价单未指定保护价。

---

## 必背规则

1. ⚠️ **优先用 `order_value` / `order_target_value`**，不要手动算 amount
2. ⚠️ **A 股 amount 须为 100 整数倍**（`order_value` 自动处理）
3. ⚠️ **禁止在 `before_trading_start` / `after_trading_end` 下单**
4. ⚠️ **同一股票不能同时挂买单和卖单**——会冲突
5. ⚠️ **`order_target(s, 0)` 是最简单的清仓写法**
6. ⚠️ **`order_target` / `order_target_value` 自动取消该标的未完成订单**
7. ⚠️ **科创板市价单必须指定保护价 `MarketOrderStyle(price)`**
8. ⚠️ **期货平仓用 `close_today` 控制平今/平昨费率**

---

## AI 常编错的下单 API

| AI 编的 | 实际应该用 |
|---|---|
| `place_order(...)` | `order(...)` 或 `order_value(...)` |
| `submit_order(...)` | `order(...)` |
| `buy_stock(s, n)` | `order(s, n)` |
| `sell_stock(s, n)` | `order(s, -n)` |
| `set_position(s, value)` | `order_target_value(s, value)` |
| `close_position(s)` | `order_target(s, 0)` |
