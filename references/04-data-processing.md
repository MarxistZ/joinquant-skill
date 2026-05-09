# 04 — 数据处理函数

> 因子数据预处理三件套：中性化、去极值、标准化。全部来自 `jqfactor` 包。

## neutralize 中性化

```python
from jqfactor import neutralize

neutralize(series, how=None, date=None, axis=1, fillna=None, add_constant=False)
```

消除因子数据中的行业、市值等风格偏差，剥离出"纯因子"信号。

**参数**：

- `series`：`pd.Series` / `pd.DataFrame`，待中性化数据，index 为股票代码
- `how`：中性化因子列表，默认 `['jq_l1', 'market_cap']`。支持：
  - 财务数据：`'market_cap'`, `'net_profit'`, `'ln_market_cap'`（对数市值）, `'ln_circulating_market_cap'`（对数流通市值）
  - 行业分类：`'jq_l1'`（聚宽一级）、`'jq_l2'`、`'sw_l1'`（申万一级）、`'sw_l2'`、`'sw_l3'`
  - 行业代码：`'HY001'` 等（传入行业代码列表等效于传入该行业分类代码）
  - 聚宽因子库因子名，如 `'operating_profit_ttm'`, `'VOL240'`
  - 风险因子：`['size', 'beta', 'momentum', 'residual_volatility', 'non_linear_size', 'book_to_price_ratio', 'liquidity', 'earnings_yield', 'growth', 'leverage']`
- `date`：日期（str），用该天的相关变量数据做中性化。**不要传 `datetime.date.today()`** —— 当天财务数据可能还未更新，导致依赖数据为 NaN，此时函数会直接返回原始数据，不做中性化
- `axis`：DataFrame 时生效，0=按列，1=按行（默认）
- `fillna`：缺失值填充方式，传行业分类代码（如 `'jq_l1'`），按该行业均值填充。默认 `None` 不填充
- `add_constant`：是否添加常数项，默认 `False`

**返回**：中性化后的因子数据

**示例**：

```python
import pandas as pd
import numpy as np
from jqfactor import neutralize

data = pd.DataFrame(
    np.random.rand(3, 300),
    columns=get_index_stocks('000300.XSHG', date='2018-05-02'),
    index=['a', 'b', 'c']
)
neutralize(data, how=['jq_l1', 'market_cap'], date='2018-05-02', axis=1)
```

---

## winsorize 去极值（标准差法）

```python
from jqfactor import winsorize

winsorize(series, scale=None, range=None, qrange=None, inclusive=True, inf2nan=True, axis=1)
```

将极端值替换为边界值（缩尾），消除异常值干扰。`scale` / `range` / `qrange` 三选一，不可同时使用。

**参数**：

- `series`：`pd.Series` / `pd.DataFrame` / `np.ndarray`
- `scale`：标准差倍数，边界为 `[mu - scale * sigma, mu + scale * sigma]`
- `range`：上下边界列表，如 `[-3, 3]`
- `qrange`：分位数边界，值在 0~1 之间，如 `[0.05, 0.95]`
- `inclusive`：`True`（默认）将超出值替换为边界值；`False` 替换为 `NaN`
- `inf2nan`：缩尾前是否先将 `±inf` 替换为 `NaN`（默认 `True`）。设为 `False` 则 `inf` 被视为在上界之上、`-inf` 在下界之下
- `axis`：DataFrame 时，0=按列，1=按行（默认）

**示例**：

```python
from jqfactor import winsorize

winsorize(data, qrange=[0.05, 0.93], inclusive=True, inf2nan=True, axis=1)
```

---

## winsorize_med 中位数去极值（MAD 法）

```python
from jqfactor import winsorize_med

winsorize_med(series, scale=1, inclusive=True, inf2nan=True, axis=1)
```

使用中位数和中位数绝对偏差（MAD）去极值。边界为 `[med - scale * MAD, med + scale * MAD]`。对非正态分布的因子更稳健。

**参数**：

- `series`：`pd.Series` / `pd.DataFrame` / `np.ndarray`
- `scale`：倍数，默认 `1.0`
- `inclusive`：`True`（默认）将超出值替换为边界值；`False` 替换为 `NaN`
- `inf2nan`：同 `winsorize`
- `axis`：同 `winsorize`

**示例**：

```python
from jqfactor import winsorize_med

winsorize_med(data, scale=1, inclusive=True, inf2nan=True, axis=0)
```

---

## standardlize 标准化（z-score）

```python
from jqfactor import standardlize

standardlize(series, inf2nan=True, axis=1)
```

将因子转换为均值为 0、标准差为 1 的标准正态分布。

**注意拼写**：是 `standardlize` 不是 `standardize`！聚宽 API 就这么定的。

**参数**：

- `series`：`pd.Series` / `pd.DataFrame` / `np.ndarray`
- `inf2nan`：是否将 `±inf` 替换为 `NaN`（默认 `True`）
- `axis`：DataFrame 时，0=按列，1=按行（默认）

**示例**：

```python
from jqfactor import standardlize

standardlize(data, inf2nan=True, axis=0)
```

---

## 典型工作流

多因子选股的标准预处理流程：先去极值，再中性化，最后标准化。

```python
from jqfactor import get_factor_values, winsorize_med, neutralize, standardlize

factor_data = get_factor_values(
    securities=stocks,
    factors=['Skewness60'],
    end_date=date,
    count=1
)
raw = factor_data['Skewness60'].iloc[0]

processed = standardlize(
    neutralize(
        winsorize_med(raw, scale=3),
        how=['jq_l1', 'market_cap'],
        date=date
    )
)
```

---

## 常见失败模式

- `from jqfactor import standardize` — 正确拼写是 `standardlize`
- 同时传 `scale` 和 `qrange` 给 `winsorize` — 这三者三选一，不能混用
- `neutralize` 的 `date` 设为 `datetime.date.today()` — 当天财务数据未更新时，函数不会报错，但会**默默返回原始值**
- `axis` 方向搞反 — 对截面数据（一行多股票）用 `axis=1`
