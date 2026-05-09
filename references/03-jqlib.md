# 03 — jqlib 因子库

> 聚宽内置的因子计算库，包含 Alpha101、Alpha191 和技术分析指标三大模块。所有函数均在聚宽策略/研究环境中直接可用。

---

## Alpha 101

来源：WorldQuant LLC 论文 *101 Formulaic Alphas*。

```python
from jqlib.alpha101 import *

# 获取沪深300成分股的 alpha_001 因子值
a = alpha_001('2017-03-10', '000300.XSHG')
a.head()
# 000001.XSHE   -0.496667
# 000002.XSHE    0.226667
# 000008.XSHE   -0.043333
# 000009.XSHE   -0.093333
# 000027.XSHE   -0.030000
# Name: rank_value_boolean, dtype: float64

# 不传 index 则计算全市场股票
a = alpha_007('2014-10-22')
a['300207.XSHE']  # 0.8

# 查看公式与参数文档
alpha_101?
# Docstring: ((close - open) / ((high - low) + .001))
```

**函数签名**：`alpha_NNN(enddate, index=None)`
- `enddate` (str)：查询日期，格式 `'YYYY-MM-DD'`
- `index` (str, optional)：指数代码，如 `'000300.XSHG'`；传则计算该指数成分股。**默认为 None，此时计算全市场所有股票。**

**返回**：`pd.Series`，index 为股票代码，value 为因子值。

共 101 个函数 (`alpha_001` ~ `alpha_101`)。

---

## Alpha 191

来源：国泰君安《基于短周期价量特征的多因子选股体系》。

```python
from jqlib.alpha191 import *

end_date = '2017-04-04'
code = list(get_all_securities(['stock'], date=end_date).index)
a = alpha_007(code, end_date)
a['300207.XSHE']  # 1.24949

# 查看签名与公式
alpha_001?
# Signature: alpha_001(code, end_date=None)
# 公式: (-1 * CORR(RANK(DELTA(LOG(VOLUME),1)),RANK(((CLOSE-OPEN)/OPEN)),6)
```

**函数签名**：`alpha_NNN(code, end_date=None)`
- `code` (list of str)：股票代码列表。**必传，不支持单个字符串。**
- `end_date` (str, optional)：查询日期，格式 `'YYYY-MM-DD'`；默认为 `None` 时使用调用日。

**返回**：`pd.Series`，index 为股票代码，value 为因子值。

共 191 个函数 (`alpha_001` ~ `alpha_191`)。

### Alpha101 vs Alpha191 区别

| 维度 | Alpha 101 | Alpha 191 |
|------|-----------|-----------|
| 第一个参数 | `enddate`（日期） | `code`（股票列表） |
| 第二个参数 | `index`（指数代码，可选） | `end_date`（日期，可选） |
| index 默认 | `None` → 全市场 | 无此参数 |
| code 默认 | 无此参数 | **必传** |
| 来源 | WorldQuant | 国泰君安 |
| 函数数量 | 101 | 191 |

---

## technical_analysis 技术分析指标

基于通达信、东方财富、同花顺的公式实现。所有指标函数通过 `from jqlib.technical_analysis import *` 导入。

```python
from jqlib.technical_analysis import *

# 单只股票
s1 = '000001.XSHE'
gdx_jax, gdx_ylx, gdx_zcx = GDX(s1, check_date='2017-01-04', N=30, M=9)
print(gdx_jax[s1])  # 济安线

# 批量股票
s_list = ['000001.XSHE', '000002.XSHE']
gdx_jax, gdx_ylx, gdx_zcx = GDX(s_list, check_date='2017-01-04', N=30, M=9)
for s in s_list:
    print(gdx_jax[s], gdx_ylx[s], gdx_zcx[s])
```

**通用签名**：`INDICATOR(security_list, check_date, **params)`
- `security_list` (str | list of str)：股票代码（单个字符串或列表）
- `check_date` (str)：查询日期，格式 `'YYYY-MM-DD'`
- `N`, `M` 等参数：各指标特有参数，见下文

**返回类型**：`dict`，key 为股票代码，value 为指标值。多返回值指标（如 GDX 返回三条线）以 tuple 形式返回多个 dict。

**常见指标一览**（完整列表见[数据字典](https://www.joinquant.com/help/api/helpname=technicalanalysis)）：

| 函数 | 名称 | 参数 | 返回值 |
|------|------|------|--------|
| `GDX` | 济安线 | N=30, M=9 | (jax, ylx, zcx) 三个 dict |
| `MACD` | 指数平滑异同平均 | SHORT=12, LONG=26, MID=9 | (DIF, DEA, MACD) 三个 dict |
| `KDJ` | 随机指标 | N=9, M1=3, M2=3 | (K, D, J) 三个 dict |
| `RSI` | 相对强弱指标 | N1=6, N2=12, N3=24 | (rsi1, rsi2, rsi3) 三个 dict |
| `BOLL` | 布林线 | N=20 | (upper, mid, lower) 三个 dict |

**注意事项**：
- 动态复权会影响技术指标计算结果，详见聚宽社区文档。
- **不要拼错 import**：`from jqlib.technical_analysis import *`，而非 `from jqlib.alpha101 import *`（常见 AI 编错）。
- 每个指标的参数个数和含义不同，使用前建议用 `INDICATOR?` 查看 docstring。

---

## jqfactor 因子数据库

与 jqlib 密切相关但属于 `jqfactor` 包的因子数据获取函数。

### get_all_factors

```python
from jqfactor import get_all_factors
print(get_all_factors())
# DataFrame：因子代码、因子名称、因子分类
```

### get_factor_values ★

```python
from jqfactor import get_factor_values

factor_data = get_factor_values(
    securities=['000001.XSHE'],
    factors=['Skewness60'],
    start_date='2017-01-01',
    end_date='2017-03-04'
)
```

**参数**：
- `securities` (str | list of str)：股票池
- `factors` (str | list of str)：因子名称
- `start_date` (str)：开始日期（与 `count` 二选一）
- `end_date` (str)：结束日期
- `count` (int)：截止 `end_date` 之前的交易日数量（与 `start_date` 二选一）

**返回**：`dict`，key 为因子名称，value 为 `pd.DataFrame`（index=日期, columns=股票代码）。

**限额**：每次请求 `因子数 x 股票数 x 交易日数 <= 200000`。超限会报错。

### get_factor_kanban_values

```python
from jqfactor import get_factor_kanban_values

df = get_factor_kanban_values(
    universe='hs300',
    bt_cycle='month_3',
    model='long_only',
    category=['quality', 'basics', 'emotion', 'growth', 'risk', 'pershare'],
    skip_paused=False,
    commision_slippage=0
)
```

---

## 常见失败模式

- `from jqlib import alpha101` -> 正确：`from jqlib.alpha101 import *`
- `from jqfactor import alpha101` -> `alpha101` 在 `jqlib` 里，不在 `jqfactor` 里
- 混淆 Alpha101 和 Alpha191 的参数顺序（101 先日期，191 先股票列表）
- Alpha191 的 `code` 传了字符串而非列表 -> 应传 `['000001.XSHE']` 而非 `'000001.XSHE'`
- `get_factor_values` 请求量超过 200,000 限额
