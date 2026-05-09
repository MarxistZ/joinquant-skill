# 02 — 数据获取函数

> 聚宽里所有"取价格、取财务、取因子"的入口。**最易出错的一类**——AI 经常编造不存在的 `get_stock_data` / `get_history_data`。

---

## 价格类（最常用）

### `get_price(security, ...)` ★

最核心的取价 API，可在回测和研究中使用。

```python
df = get_price(
    security='000001.XSHE',          # 单标的或 list
    start_date=None,                 # 与 count 二选一
    end_date=None,                   # 默认 '2015-12-31'
    frequency='daily',               # 'daily'/'1d'/'Xd'/ 'minute'/'1m'/'Xm'
    fields=None,                     # None=全部标准字段，支持 open/close/high/low/
                                     #   volume/money/factor/high_limit/low_limit/
                                     #   avg/pre_close/paused/open_interest
    skip_paused=False,               # True 跳过停牌（多标的时需 panel=False）
    fq='pre',                        # 'pre'前复权 / 'post'后复权 / None 不复权
    count=None,                      # 与 start_date 二选一
    panel=True,                      # ⚠️ 默认 True，pandas 0.25 后 Panel 已移除，建议 False
    fill_paused=True,                # True 用 pre_close 填充停牌 / False 用 NaN
)
```

**返回**：单标的 → DataFrame（行=日期，列=字段）；多标的 + `panel=True` → Panel（已废弃）；多标的 + `panel=False` → DataFrame（MultiIndex）

**关键提醒**：
- ⚠️ `start_date` 和 `count` **互斥**
- ⚠️ `panel` 默认 `True`，但 pandas 已移除 Panel。多标的**务必设置 `panel=False`**
- ⚠️ 回测里 `end_date` 不要大于 `context.current_dt`，否则引入未来函数
- ⚠️ 回测里用 `count` 而不是硬编码 `start_date`，避免未来函数
- ⚠️ `fq` 参数：研究环境默认 `'pre'`；回测开 `use_real_price=True` 时价格已是真实价
- ⚠️ `frequency` 支持 `'Xd'`/`'Xm'`（X 正整数），>1 时 fields 仅支持标准字段

### `get_bars(security, count, unit, ...)` ★

数据快照 API，**没有 skip_paused 选项**，停牌日直接跳过不填充。返回 numpy 或 DataFrame。

```python
arr = get_bars(
    security='000001.XSHE',          # 单标的字符串或 list
    count=5,                         # 获取 bar 个数（不足则返回实际个数）
    unit='1d',                       # '1m'/'5m'/'15m'/'30m'/'60m'/'120m'/
                                     #   '1d'/'1w'(周)/'1M'(月) 或 'Xm' 非标准
    fields=['date', 'open', 'high', 'low', 'close'],  # 支持 open/close/high/low/
                                     #   volume/money/date/open_interest/factor
    include_now=False,               # True=包含当前未完成 bar
    end_dt=None,                     # 默认 context.current_dt 或 datetime.now()
    fq_ref_date=None,                # None=不复权；设日期=以该日为基准定点复权
    df=False,                        # True 返回 DataFrame；False 返回 ndarray
)
```

**返回**：单标的 + `df=False` → ndarray；多标的 + `df=False` → dict{code: ndarray}；`df=True` → DataFrame（多标的多重索引）

**关键提醒**：
- ⚠️ 不跳过停牌——停牌日直接跳过，bar 个数可能 < count
- ⚠️ `fields` 默认不含 `volume`/`money`，需要显式追加
- ⚠️ 开盘第一根 bar 的高开低收都是开盘价，量=0
- ⚠️ `fq_ref_date` 为 `None` = 不复权；设 `datetime.now()` = 前复权；设很早日期 = 后复权

### `attribute_history(security, count, unit, fields, ...)` ★

回测里用得最多。**默认从当前时间往回取，自动避免未来函数**。**回测首选**。

```python
df = attribute_history(
    security='000001.XSHE',
    count=20,                        # 取多少根
    unit='1d',                       # '1d'/'1m'/'5m'/'15m'/'30m'/'60m'/'120m'/'Xd'/'Xm'
    fields=['open', 'close', 'high', 'low', 'volume', 'money'],
    skip_paused=True,                # ⚠️ 默认 True（和 get_price 不同！）
    df=True,                         # True→DataFrame, False→dict{field: ndarray}
    fq='pre',
)
```

**返回**：`df=True` → DataFrame（行=日期，列=字段）；`df=False` → dict

**关键提醒**：
- 天数据**不包含当天**（即使收盘后）；分钟数据不包含当前分钟
- `df=False` 性能更好（无 DataFrame 创建开销），回测慢时可考虑
- ⚠️ `skip_paused` 默认 `True`（和 `get_price` 默认 `False` 相反！）

### `history(count, unit, field, security_list, ...)`

`attribute_history` 的多标的版。取**单个字段**的多标的。

```python
df = history(
    count=20, unit='1d', field='avg',   # field 是单个字段
    security_list=None,                  # None = context.universe
    df=True, skip_paused=False, fq='pre',
)
```

**返回**：`df=True` → DataFrame（行=日期，列=股票代码）；`df=False` → dict{code: ndarray}

**关键提醒**：
- `field` 是**单个字段**（和 `attribute_history` 的 `fields` 列表不同！）
- `security_list=None` 前需 `set_universe(list)` 设定
- 天数据不包含当天，分钟数据不包含当前分钟
- `df=False` 性能更好

### `get_current_data()` ★

取**当前 tick** 的实时数据（涨跌停、最新价、是否停牌等）。**回测/模拟专用**。

```python
cd = get_current_data()
print(cd['000001.XSHE'].last_price)    # 最新价
print(cd['000001.XSHE'].high_limit)    # 涨停价
print(cd['000001.XSHE'].low_limit)     # 跌停价
print(cd['000001.XSHE'].paused)        # 是否停牌
print(cd['000001.XSHE'].is_st)         # 是否 ST
print(cd['000001.XSHE'].day_open)      # 当天开盘价（09:27 后可获取）
print(cd['000001.XSHE'].name)          # 当前股票名称
print(cd['000001.XSHE'].industry_code) # 所属行业代码
```

**用途**：判断涨跌停、停牌、ST 等。

**注意**：dict 按需加载（访问时才会获取）；结果仅当天有效，不要存；仅在交易时段调用。

### `get_current_tick(security, dt, df)` ★

获取**最新一条 tick** 数据。回测/模拟专用（研究不支持）。

```python
tick = get_current_tick('000001.XSHE')                              # 返回 tick 对象
tick = get_current_tick('000001.XSHE', dt=datetime(2018,11,1,10,0,0))  # 指定时刻最近 tick
tick = get_current_tick(['000001.XSHE', '600000.XSHG'])              # list → dict
tick_df = get_current_tick('000001.XSHE', df=True)                   # DataFrame 格式
```

**用途**：在 `run_daily` / `handle_data` / `handle_tick` 中取实时快照。

### `get_ticks(security, end_dt, start_dt, count, fields, skip, df)`

取历史 tick 序列（股票 2010 年起，期货、期权、场内基金）。

```python
ticks = get_ticks(
    security='000001.XSHE',          # 单标的或 list
    end_dt='2018-07-02',             # 结束时间
    start_dt=None,                   # 与 count 二选一
    count=10,                        # 与 start_dt 二选一
    fields=['time', 'current', 'high', 'low', 'volume', 'money'],
    skip=True,                       # True=过滤无成交变化的 tick
    df=False,                        # True=DataFrame
)
```

**提醒**：`skip=True` 时集合竞价期间无成交则返回空；`df=True` 可显示字段名。

### `get_call_auction(security, start_date, end_date, fields)`

取每日 09:25 集合竞价 tick（含五档买卖盘）。

```python
df = get_call_auction(
    security=['000001.XSHE', '000002.XSHE'],
    start_date='2019-01-01',         # ⚠️ 必填！
    end_date='2019-10-10',           # ⚠️ 必填！
    fields=['time', 'current', 'a1_v', 'b1_v'],
)
```

**返回**：DataFrame（行=每只标的每日数据），最多 5000 行。

**提醒**：`start_date`/`end_date` **均不可为 None**，否则抛异常；`fields=None` 取全部字段。

---

## 财务数据

### `get_fundamentals(query_object, date, statDate)` ★

取财务数据（PE/市值/利润等）。需构造 `query` 对象。

```python
q = query(
    valuation.code, valuation.pe_ratio, valuation.market_cap,
    indicator.roe,
).filter(
    valuation.code.in_(stocks)
).order_by(
    valuation.market_cap.asc()
).limit(50)

df = get_fundamentals(q, date='2023-06-30')
```

**`date` vs `statDate`**（二选一）：
- `date`：查指定日期**收盘后能看到的最近数据**（默认=回测 `context.current_dt` 前一天/研究最新日期）
- `statDate`：查指定季度/年份的财报，格式 `'2015q1'` / `'2015'`
- ⚠️ 用 `statDate` 查财报可能有未来函数（发布延迟）
- ⚠️ 银行业/券商/保险专项数据只有年报，需用 `statDate`

**字段命名空间**：
- `valuation.*` —— 估值（pe, pb, market_cap, ps, turnover_ratio...）
- `balance.*` —— 资产负债表
- `income.*` —— 利润表
- `cash_flow.*` —— 现金流量表
- `indicator.*` —— 财务指标（roe, roa, eps...）

**限制**：最多返回 **5000 行**；`limit()` 默认 100。

### `get_fundamentals_continuously(query_object, end_date, count, panel)`

查**连续多天**的财务数据（如连续多日的市值、估值）。

```python
q = query(valuation.turnover_ratio, valuation.market_cap, indicator.eps
    ).filter(valuation.code.in_(['000001.XSHE', '600000.XSHG']))

panel = get_fundamentals_continuously(q, end_date='2018-01-01', count=5, panel=False)
```

**限制**：股票数 x count ≤ 5000，否则数据不完整。

### `get_history_fundamentals(security, fields, ...)`

取**多个季度/年度**的历史财报（跨期对比）。

```python
df = get_history_fundamentals(
    security=['000001.XSHE', '600000.XSHG'],
    fields=[balance.cash_equivalents, income.total_operating_revenue],
    watch_date=None,          # 与 stat_date 二选一，观察日期
    stat_date='2019q1',       # 或 '2019'，与 watch_date 二选一
    count=5,                  # 历史报告期数量
    interval='1q',            # '1q'每季度 / '1y'每年
    stat_by_year=False,       # True=返回年报数据（interval 须 '1y'）
)
```

**注意**：不支持 `valuation` 市值表；最多返回 5000 条。

### `get_valuation(security, start_date, end_date, fields, count)`

快速取多标的连续多日的**市值表数据**（不用写 query）。

```python
df = get_valuation(
    '000001.XSHE',
    end_date='2019-11-18',
    count=3,
    fields=['capitalization', 'market_cap', 'pe_ratio', 'pb_ratio'],
)
```

**可用字段**：`capitalization`, `circulating_cap`, `market_cap`, `circulating_market_cap`, `turnover_ratio`, `pe_ratio`, `pe_ratio_lyr`, `pb_ratio`, `ps_ratio`, `pcf_ratio`

**注意**：不要取当天数据（pe/市值盘后更新）；最多 5000 条。

### `finance.run_query(query_object)`

查深沪港通、股东信息、公司概况等（需构造 query）。

```python
q = query(finance.STK_AH_PRICE_COMP
    ).filter(finance.STK_AH_PRICE_COMP.a_code == '000002.XSHE'
    ).limit(10)
df = finance.run_query(q)
```

**注意**：最多 4000 行；**不支持连表查询**。

### `macro.run_query(query_object)`

查宏观经济数据（利率、GDP、CPI 等）。

```python
q = query(macro.MAC_INDUSTRY_AREA_AGR_OUTPUT_VALUE_QUARTER).limit(10)
df = macro.run_query(q)
```

**注意**：最多 4000 行；**不支持连表查询**。

---

## 因子数据

### `get_all_factors()`

获取聚宽因子库中**所有因子列表**。

```python
from jqfactor import get_all_factors
factors_df = get_all_factors()
# 返回 DataFrame：index, factor(因子代码), factor_intro(因子名称), category(分类)
```

### `get_factor_values(securities, factors, start_date, end_date, count)` ★

取**聚宽预计算因子**的值（比自己算快得多）。**从 `jqfactor` 导入**。

```python
from jqfactor import get_factor_values

fv = get_factor_values(
    securities=['000001.XSHE', '000002.XSHE'],
    factors=['pe_ratio', 'momentum_20d', 'volatility_60d'],
    start_date='2023-01-01',          # 与 count 二选一
    end_date='2023-06-30',
    # count=10,                       # 与 start_date 二选一
)
# fv: dict{因子名: DataFrame(行=日期, 列=股票代码)}
```

**限制**：因子值总数（因子数 x 股票数 x 天数）≤ 200000。

### `get_factor_kanban_values(universe, bt_cycle, model, category, ...)`

获取因子看板绩效（IC、夏普、收益等）。

```python
from jqfactor import get_factor_kanban_values
df = get_factor_kanban_values(
    universe='hs300',                 # 'hs300'/'zz500'/'zz800'/'zz1000'/'zzqz'
    bt_cycle='month_3',              # 'month_3'/'year_1'/'year_3'/'year_10'
    model='long_only',               # 'long_only'/'long_short'
    category=['quality', 'basics', 'emotion', 'growth', 'risk', 'pershare'],
    skip_paused=False,
    commision_slippage=0,            # 0=无 / 1=3‱佣金+1‰印花税 / 2=加1‰滑点
)
```

---

## 股票池 / 标的池

### `get_all_securities(types, date)` ★

取所有标的，`types` 列表（空 = 仅股票）：

```python
all_stocks = get_all_securities(['stock', 'fund', 'etf', 'lof', 'fja', 'fjb',
                                 'open_fund', 'bond_fund', 'stock_fund',
                                 'QDII_fund', 'money_market_fund', 'mixture_fund',
                                 'index', 'futures', 'options'])
```

**返回**：DataFrame（index=代码，columns: `display_name`/`name`/`start_date`/`end_date`/`type`）

**注意**：`end_date` 未退市为 `2200-01-01`；建议加 `date` 参数限定日期。

### `get_security_info(code, date)`

```python
info = get_security_info('000001.XSHE', date='2023-06-30')
# .display_name / .name / .start_date / .end_date / .type / .parent(分级母基金)
```

### `get_index_stocks(index_symbol, date)`

```python
hs300 = get_index_stocks('000300.XSHG', date='2023-06-30')
zz500 = get_index_stocks('000905.XSHG')
```

### `get_index_weights(index_id, date)`

获取指数成分股**权重**（每月更新）。

```python
w = get_index_weights(index_id='000001.XSHG', date='2018-05-09')
# 返回 DataFrame：code / display_name / date / weight
```

### `get_industry_stocks(industry_code, date)`

```python
banks = get_industry_stocks('801780', date='2023-06-30')  # 申万银行
```

### `get_concept_stocks(concept_code, date)`

```python
ai_stocks = get_concept_stocks('GN034', date='2023-06-30')  # AI 概念
```

### `get_industries(name, date)`

获取行业**列表**。

```python
df = get_industries(name='sw_l1', date='2023-06-30')
# name: 'sw_l1'/'sw_l2'/'sw_l3'/'jq_l1'/'jq_l2'/'zjw'（证监会）
```

### `get_concepts()`

获取所有概念板块列表。

```python
df = get_concepts()
# index=概念代码, columns: name, start_date
```

---

## 行业 / 概念分类

### `get_industry(security, date)` ★

```python
ind = get_industry(['000001.XSHE', '000002.XSHE'], date='2018-06-01')
print(ind['000001.XSHE']['jq_l1'])   # 聚宽一级：{'industry_code':'HY007','industry_name':'金融指数'}
print(ind['000001.XSHE']['sw_l1'])   # 申万一级
print(ind['000001.XSHE']['sw_l2'])   # 申万二级
print(ind['000001.XSHE']['sw_l3'])   # 申万三级
print(ind['000001.XSHE']['zjw'])     # 证监会
```

### `get_concept(security, date)`

```python
con = get_concept('000001.XSHE', date='2019-07-15')
print(con['000001.XSHE']['jq_concept'])
# [{'concept_code': 'GN001', 'concept_name': '5G概念'}, ...]
```

---

## 交易日

### `get_all_trade_days()`

```python
from jqdata import *
days = get_all_trade_days()    # numpy.ndarray of datetime.date
```

### `get_trade_days(start_date, end_date, count)`

```python
from jqdata import *
days = get_trade_days(start_date='2023-01-01', end_date='2023-12-31')
days = get_trade_days(end_date='2023-12-31', count=60)   # 后60个交易日
```

**注意**：`start_date` 和 `count` 互斥。最多取到当前年份最后一天。

### `get_trade_day(security, query_dt)`

根据标的具体时刻**获取对应的交易日**。对有夜盘品种重要。

```python
d = get_trade_day(["RB1901.XSGE", "000001.XSHE"], query_dt="2019-01-04 22:00:00")
# {'RB1901.XSGE': datetime.date(2019, 1, 7), '000001.XSHE': datetime.date(2019, 1, 4)}
```

---

## 其他常用

### `get_extras(info, security_list, start_date, end_date, df, count)`

```python
df = get_extras(
    info='is_st',                        # 'is_st'/'acc_net_value'/'unit_net_value'/
    security_list=['000001.XSHE'],       #   'futures_sett_price'/'futures_positions'/
    start_date='2023-01-01',             #   'adj_net_value'
    end_date='2023-06-30',
    df=True,
    # count=None,                        # 与 start_date 二选一
)
```

### `get_money_flow(security_list, start_date, end_date, fields, count)`

资金流向（主力净额、超大单、大单等），仅股票，2010 年至今日频。

```python
from jqdata import *
df = get_money_flow('000001.XSHE', start_date='2016-02-01', end_date='2016-02-04')
```

**字段**：`change_pct`(涨跌幅), `net_amount_main`(主力净额万), `net_pct_main`, `net_amount_xl`(超大单), `net_pct_xl`, `net_amount_l`(大单), `net_amount_m`(中单), `net_amount_s`(小单)

**注意**：回测中可能比 count 少一条（避免未来函数）。

### `get_billboard_list(stock_list, start_date, end_date, count)`

获取**龙虎榜**数据。

```python
df = get_billboard_list(stock_list=None, end_date=context.previous_date, count=1)
# 返回：code / day / direction / abnormal_code / sales_depart_name / rank /
#       buy_value / sell_value / net_value / amount ...
```

### `get_locked_shares(stock_list, start_date, end_date)`

取**限售解禁**数据。

---

## 期货专用

### `get_dominant_future(underlying_symbol, date)`

取主力合约。

```python
ifc = get_dominant_future('IF', date='2023-06-30')  # 返回 'IF2306.CCFX'
```

### `get_future_contracts(underlying_symbol, date)`

取所有合约。

详见 `references/12-futures.md`。

---

## 必背规则

1. ⚠️ **回测里取历史数据，首选 `attribute_history` / `history`**——自动避免未来函数，不用管 `end_date`
2. ⚠️ **多标的取数据时用 panel/dict 模式，不要 for 循环**——性能差很多
3. ⚠️ **`fq` 参数和 `set_option('use_real_price', True)` 的关系**：开启真实价格后，所有取价 API 自动按当日复权因子前复权
4. ⚠️ **聚宽预计算因子比自己算快**：能用 `get_factor_values` 就别用 `get_fundamentals` + 手算
5. ⚠️ **`get_bars` 没有 skip_paused**——停牌日直接跳过，不填充，返回个数可能 < count
6. ⚠️ **`attribute_history` 的 `skip_paused` 默认 True**，`get_price` 默认 False——混用易踩坑
7. ⚠️ **financial query 的 limit 默认 100**——大池子要显式指定 `.limit(N)`（上限 5000）
8. ⚠️ **`get_fundamentals` 的 `date` 默认 = `context.current_dt` 前一天**（回测），不要传当天日期取 pe/市值
9. ⚠️ **`get_price(panel=True)` 已废弃**——pandas 移除了 Panel，多标的一律用 `panel=False`
10. ⚠️ **`get_current_data()` 仅在交易时段可调用**，且结果仅当天有效

---

## AI 常编错的 API

| AI 编的 | 实际应该用 |
|---|---|
| `get_stock_data(code)` | `get_price(code, ...)` 或 `attribute_history(code, ...)` |
| `get_history_data(code, days)` | `attribute_history(code, days, '1d', ['close'])` |
| `jqdata.fetch_data(...)` | 不存在的命名空间，直接用 `get_price` |
| `get_realtime_quote(code)` | `get_current_data()[code].last_price` |
| `get_index_constituents('hs300')` | `get_index_stocks('000300.XSHG')` |
| `get_account_balance()` | `context.portfolio.available_cash` |
| `get_position(code)` | `context.portfolio.positions.get(code)` |
| `get_fundamentals(q, statDate=...)` with valuation | 不支持！valuation 用 `get_valuation()` 或 `get_fundamentals(date=...)` |
| `get_stock_industry(code)` | `get_industry(code)` |
| `get_current_tick()` without args | `get_current_tick(security)` — 必须传标的 |
