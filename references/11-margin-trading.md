# 11 — 融资融券

> 聚宽支持融资买入、融券卖出、直接还款还券等两融操作。需初始化 `type='stock_margin'` 类型账户，默认 `type='stock'` 不允许两融操作。

---

## 初始化融资融券账户

```python
def initialize(context):
    set_subportfolios([SubPortfolioConfig(
        cash=context.portfolio.starting_cash, type='stock_margin'
    )])
```

**多账户混合**（同时使用普通股票 + 期货 + 两融）：

```python
def initialize(context):
    init_cash = context.portfolio.starting_cash / 3
    set_subportfolios([
        SubPortfolioConfig(cash=init_cash, type='stock'),
        SubPortfolioConfig(cash=init_cash, type='index_futures'),
        SubPortfolioConfig(cash=init_cash, type='stock_margin'),
    ])
```

`pindex` 参数在各交易函数中用于指定操作哪个子账户（从 0 开始）。

---

## 利率和保证金设置

通过 `set_option` 配置，可在 `initialize` 中调用：

```python
set_option('margincash_interest_rate', 0.08)   # 融资利率，默认 8%（年化）
set_option('margincash_margin_rate', 1.5)      # 融资保证金比率，默认 100%（1.0）
set_option('marginsec_interest_rate', 0.10)    # 融券利率，默认 10%（年化）
set_option('marginsec_margin_rate', 1.5)       # 融券保证金比率，默认 100%（1.0）
```

注意：保证金比率 1.5 = 150%，即需要 150% 市值的担保品。

---

## 融资操作

### margincash_open — 融资买入

```python
margincash_open(security, amount, style=None, pindex=0)
```

| 参数 | 说明 |
|---|---|
| `security` | 标的代码 |
| `amount` | 买入数量（股） |
| `style` | OrderStyle 对象，None 等价于 MarketOrder（市价单） |
| `pindex` | 子账户序号，默认 0 |

**返回**：Order 对象（委托成功）或 None（失败）。

```python
margincash_open('000001.XSHE', 1000)
```

### margincash_close — 卖券还款

```python
margincash_close(security, amount, style=None, pindex=0)
```

参数同上。卖出持仓偿还融资负债。

**返回**：Order 对象或 None。

```python
margincash_close('000001.XSHE', 1000)
```

### margincash_direct_refund — 直接还款

```python
margincash_direct_refund(value, pindex=0)
```

| 参数 | 说明 |
|---|---|
| `value` | 还款金额（元） |
| `pindex` | 子账户序号，默认 0 |

**返回**：None。

```python
margincash_direct_refund(100000)
```

---

## 融券操作

### marginsec_open — 融券卖出

```python
marginsec_open(security, amount, style=None, pindex=0)
```

参数同 `margincash_open`。

**返回**：Order 对象或 None。

```python
marginsec_open('000001.XSHE', 1000)
```

### marginsec_close — 买券还券

```python
marginsec_close(security, amount, style=None, pindex=0)
```

买入证券偿还融券负债。

**返回**：Order 对象或 None。

```python
marginsec_close('000001.XSHE', 1000)
```

### marginsec_direct_refund — 直接还券

```python
marginsec_direct_refund(security, amount, pindex=0)
```

| 参数 | 说明 |
|---|---|
| `security` | 标的代码 |
| `amount` | 还券数量（股） |
| `pindex` | 子账户序号，默认 0 |

**返回**：None。

要求账户中有对应股票的足够持仓，否则需先买入再还：

```python
# 方案 A：持仓已有 1000 股 → 直接还
marginsec_direct_refund('000001.XSHE', 1000)

# 方案 B：持仓不足 → 先买入再还
order('000001.XSHE', 1000)
marginsec_direct_refund('000001.XSHE', 1000)
```

---

## 融资融券标的查询

### get_margincash_stocks — 融资标的列表

```python
get_margincash_stocks()
```

**返回**：list，上交所、深交所最近一次披露的可融资标的代码列表。

*（可选参数 `date`：指定查询日期，回测中默认当日，研究中默认最新。）*

```python
margincash_stocks = get_margincash_stocks()
'000001.XSHE' in get_margincash_stocks()  # True
```

### get_marginsec_stocks — 融券标的列表

```python
get_marginsec_stocks(date=None)
```

| 参数 | 说明 |
|---|---|
| `date` | 查询日期，回测中默认当日，研究中默认最新 |

**返回**：list，可融券标的代码列表。

```python
marginsec_stocks = get_marginsec_stocks()
'000001.XSHE' in get_marginsec_stocks()  # True
```

**注意**：`get_margincash_stocks` 和 `get_marginsec_stocks` 均无法获取当前未完结交易日的数据，因为交易所数据尚未生成。

### get_mtss — 融资融券历史信息

需导入 `jqdata`：

```python
from jqdata import *
get_mtss(security_list, start_date=None, end_date=None, fields=None, count=None)
```

| 参数 | 说明 |
|---|---|
| `security_list` | 单只股票代码或 list |
| `start_date` | 开始日期，与 `count` 二选一，不可同时使用，默认为平台提供的数据最早日期 |
| `end_date` | 结束日期，默认当天 |
| `count` | 取 `end_date` 之前 count 个交易日（含 end_date），必须大于 0，与 `start_date` 二选一 |
| `fields` | 字段名（字符串）或 list，默认全部字段 |

**返回**：pandas DataFrame。

**字段说明**：

| 字段 | 含义 |
|---|---|
| `date` | 日期 |
| `sec_code` | 股票代码 |
| `fin_value` | 融资余额（元） |
| `fin_buy_value` | 融资买入额（元） |
| `fin_refund_value` | 融资偿还额（元） |
| `sec_value` | 融券余量（股） |
| `sec_sell_value` | 融券卖出量（股） |
| `sec_refund_value` | 融券偿还量（股） |
| `fin_sec_value` | 融资融券余额（元） |

```python
from jqdata import *

# 单只股票，指定起止日期
get_mtss('000001.XSHE', '2016-01-01', '2016-04-01')

# 多只股票，筛选字段
get_mtss(['000001.XSHE', '000002.XSHE'], '2015-03-25', '2016-01-25',
         fields=['date', 'sec_code', 'fin_value'])

# 指定单个字段（字符串格式）
get_mtss('000001.XSHE', '2016-01-01', '2016-04-01', fields='sec_sell_value')

# 用 count 取最近 N 个交易日（end_date 之前）
get_mtss('000001.XSHE', end_date='2016-06-30', count=20)

# 不指定 end_date，默认今天
get_mtss('000001.XSHE', count=20)
```

---

## 常见失败模式

| 错误 | 原因 |
|---|---|
| `type='stock'` 账户中调用两融函数 | 类型不匹配，需用 `type='stock_margin'` |
| 混淆 `margincash_close` 和 `margincash_direct_refund` | 前者卖券还款，后者直接现金还款 |
| `marginsec_direct_refund` 时持仓不足 | 需先用 `order` 买入再还 |
| `get_margincash_stocks()` / `get_marginsec_stocks()` 获取当日数据 | 交易日未结束时数据不可用 |
| `get_mtss` 未导入模块 | 必须加 `from jqdata import *` |
| `get_mtss` 同时传入 `start_date` 和 `count` | 参数互斥，只能选其一 |
