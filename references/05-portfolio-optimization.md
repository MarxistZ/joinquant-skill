# 05 — 组合优化函数

> 聚宽内置的投资组合优化器，在约束条件下计算最优权重。

## portfolio_optimizer

```python
from jqlib.optimizer import *

portfolio_optimizer(
    date, securities, target, constraints,
    bounds=[Bound(0.0, 1.0)],
    default_port_weight_range=[0.0, 1.0],
    ftol=1e-9,
    return_none_if_fail=True
)
```

**参数**：
- `date`：优化发生日期，注意未来函数
- `securities`：股票代码列表
- `target`：目标函数（只能选一个，见下方）
- `constraints`：限制函数列表（可多个，见下方）
- `bounds`：边界函数列表（可多个，见下方）。默认 `[Bound(0.0, 1.0)]`
- `default_port_weight_range`：默认组合权重的和的范围 `[0.0, 1.0]`。如果 **constraints 中没有** `WeightConstraint` 或 `WeightEqualConstraint`，优化器会自动添加 `WeightConstraint(low=default_port_weight_range[0], high=default_port_weight_range[1])`
- `ftol`：优化停止精度，默认 `1e-9`。精度不够时降低，速度慢时提高
- `return_none_if_fail`：优化失败时 `True` 返回 `None`，`False` 返回全零权重

---

## 目标函数 (target)

只能选一个。

| 函数 | 说明 | 参数 |
|---|---|---|
| `MinVariance(count=250)` | 最小化组合方差 | `count`: 向前取收益率的天数 |
| `MaxProfit(count=250)` | 最大化组合收益 | `count`: 向前取收益率的天数 |
| `MaxSharpeRatio(rf=0.0, weight_sum_equal=1.0, count=250)` | 最大化夏普比率 | `rf`: 年化无风险利率；`weight_sum_equal`: 优化时组合总权重（默认 1.0） |
| `MinTrackingError(benchmark, count=250)` | 最小化追踪误差 | `benchmark`: 基准代码，如 `'000300.XSHG'` |
| `RiskParity(count=250, risk_budget=None)` | 风险平价 | `risk_budget`: pd.Series，每只标的对组合风险贡献的预算，`None` 表示各标的风险贡献相等 |
| `MaxScore(scores)` | 打分最大化（给予高分标的更高权重） | `scores`: pd.Series，每只标的的打分，index 为股票代码 |
| `MinScore(scores)` | 打分最小化（给予低分标的更高权重） | `scores`: pd.Series，每只标的的打分，index 为股票代码 |
| `MaxFactorValue(factor, count=1)` | 因子值最大化（只支持股票） | `factor`: Factor 子类；`count`: 过去几天因子值取平均 |
| `MinFactorValue(factor, count=1)` | 因子值最小化（只支持股票） | `factor`: Factor 子类；`count`: 过去几天因子值取平均 |

**Factor 子类示例**（用于 `MaxFactorValue`/`MinFactorValue`）：
```python
from jqfactor import Factor

class AR(Factor):
    name = 'AR_M5'
    max_window = 5
    dependencies = ['AR']
    def calc(self, data):
        return data['AR'].mean()

target = MaxFactorValue(factor=AR, count=1)
```

---

## 限制函数 (constraints)

可设置多个。

| 函数 | 说明 |
|---|---|
| `WeightConstraint(low=0.0, high=1.0)` | 组合总权重上下限 |
| `WeightEqualConstraint(limit=1.0)` | 组合总权重等于某值 |
| `AnnualStdConstraint(limit, count=250)` | 组合年化标准差上限 |
| `AnnualProfitConstraint(limit, count=250)` | 组合年化收益率下限 |
| `IndustryConstraint(industry_code, low=0.0, high=1.0)` | 行业（组）权重限制。`industry_code` 为单个或多个行业代码如 `'HY001'`，列表中所有行业股票的权重之和受限制 |
| `IndustriesConstraint(industry_code, low=0.0, high=1.0)` | 行业分类下所有行业权重限制。`industry_code` 为行业分类代码如 `'jq_l1'` |
| `MarketConstraint(market_type, low=0.0, high=1.0)` | 市场类型权重限制。`market_type` 可选 `'stock'`/`'index'`/`'fund'`/`'futures'`/`'etf'`/`'lof'`/`'fja'`/`'fjb'`/`'open_fund'`/`'bond_fund'`/`'stock_fund'`/`'QDII_fund'`/`'money_market_fund'`/`'mixture_fund'` |
| `ExposureConstraint(factor, low=0.0, high=1.0, count=1)` | 因子暴露限制。`factor` 为 Factor 子类 |
| `BarraConstraint(size=None, beta=None, ..., standardlize=True, winsorize=True)` | Barra 风险因子暴露限制（见下方） |
| `IndustryDeviationConstraint(industry_code, benchmark, limit)` | 单行业与基准偏离度限制。`industry_code` 为行业代码 |
| `IndustriesDeviationConstraint(industry_code, benchmark, limit)` | 行业分类与基准偏离度限制。`industry_code` 为行业分类代码如 `'jq_l1'` |
| `TrackingErrorConstraint(benchmark, limit, count=250)` | 年化追踪误差限制 |
| `TurnoverConstraint(limit, current_portfolio=None)` | 换手率限制。`current_portfolio` 为当前权重 pd.Series，`None` 视为空仓 |
| `RatioConstraint(ratio, low=None, high=None, rf=None, benchmark=None, count=250)` | 比率限制（见下方） |
| `MaxDrawdownConstraint(limit, count=250)` | 最大回撤限制，如 `limit=-0.25` |

**BarraConstraint 参数**：10 个风险因子各传 `[low, high]` 列表或 `None`（无限制）。
```
size/beta/momentum/residual_volatility/no_linear_size
/book_to_price/liquidity/earning_yield/growth/leverage
分别对应：市值/贝塔/动量/残差波动/非线性市值/账面市值比/流动性/盈利预期/成长/杠杆因子
```
```python
constraint = BarraConstraint(
    size=[-0.5, 0.5],
    beta=[None, 1.5],
    winsorize=False
)
```

**RatioConstraint 支持的 ratio**：
`sharpe_ratio`, `information_ratio`, `calmar_ratio`, `omega_ratio`, `sortino_ratio`, `var`, `cvar`

---

## 边界函数 (bounds)

对单只标的的权重限制（不涉及组合总权重）。可设置多个，最终每只标的权重下限取各 Bound 的最大值，上限取最小值。

| 函数 | 说明 |
|---|---|
| `Bound(low=0.0, high=1.0)` | 每只标的的权重范围 |
| `IndustryBound(industry_code, low=0.0, high=1.0)` | 按行业限制单股权重。属于该行业的股票权重在 `[low, high]` 内，否则权重下限为 0、上限为 1 |
| `LiquidityBound(limit, capital, count=1, subset=None)` | 流动性限制：购买数量不超过成交量的百分比。`capital`: 可用资金；`subset`: 仅约束部分股票列表 |
| `CapBound(limit, capital, count=1, subset=None)` | 市值限制：购买金额不超过总市值百分比。`capital`: 可用资金；`subset`: 仅约束部分股票列表 |

---

## 完整示例

```python
import pandas as pd
from jqdata import *
from jqfactor import Factor
from jqlib.optimizer import *

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        close_tax=0.001, open_commission=0.0003,
        close_commission=0.0003, min_commission=5
    ), type='stock')
    run_monthly(rebalance, monthday=1, time='09:31')

def rebalance(context):
    stocks = get_index_stocks('000300.XSHG')[:20]
    date = context.previous_date

    weights = portfolio_optimizer(
        date=date,
        securities=stocks,
        target=MinVariance(count=250),
        constraints=[
            WeightEqualConstraint(limit=1.0),
            AnnualStdConstraint(limit=0.15, count=250),
        ],
        bounds=[Bound(0.0, 0.1)],
    )

    if weights is not None:
        for stock, w in weights.items():
            if w > 0:
                order_target_value(stock, context.portfolio.total_value * w)
```

若想查看更多应用场景（风险平价 + 市场类型权重、最大化夏普比率 + 因子最大化等），参见示例代码文档。

---

## 常见失败模式

- 导包错误：`from jqlib import optimizer` --> `from jqlib.optimizer import *`
- 传了多个 `target` --> 只能选一个
- `date` 用了未来日期 --> 未来函数
- 优化求解超时 --> 提高 `ftol` 或减少股票数量
- 所有权重为 0 --> 约束条件矛盾，检查 constraints 和 bounds 是否冲突
- 未设置 `WeightConstraint`/`WeightEqualConstraint` 时，留意 `default_port_weight_range` 会**自动添加**默认总权重约束
