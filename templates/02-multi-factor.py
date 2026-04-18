# =============================================================================
# 模板 02：多因子选股 + 月度调仓
# =============================================================================
# 适用场景：
#   - 多因子量化选股（市值、PE、动量等组合）
#   - 月度调仓，持有 N 只股票
#   - 沪深 300 / 中证 500 成分股池
#
# 核心思路：
#   每月初按因子打分，选出排名前 N 的股票，等权重持有
# =============================================================================

import jqdata
import pandas as pd


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(FixedSlippage(0.02))

    # 策略参数
    g.universe_index = '000300.XSHG'  # 股票池：沪深 300 成分
    g.hold_num = 10                    # 持仓数量
    g.factor_pe_weight = 0.4           # 因子权重
    g.factor_market_cap_weight = 0.4
    g.factor_momentum_weight = 0.2

    # 月度调仓：每月第一个交易日 09:30
    run_monthly(rebalance, monthday=1, time='09:31')


def rebalance(context):
    """每月初执行调仓。"""

    # 1. 取股票池
    stocks = get_index_stocks(g.universe_index)

    # 2. 取因子值（PE / 总市值）
    # RATIONALE: get_fundamentals 取最近一期财务数据，没有未来函数
    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.market_cap,
    ).filter(
        valuation.code.in_(stocks)
    )
    df = get_fundamentals(q)

    if df.empty:
        log.warning('未取到基本面数据，跳过本次调仓')
        return

    # 3. 取 20 日动量（过去 20 日累计收益率）
    momentum = []
    for code in df['code']:
        prices = attribute_history(code, 21, '1d', ['close'])
        if len(prices) >= 21 and prices['close'].iloc[0] > 0:
            mom = prices['close'].iloc[-1] / prices['close'].iloc[0] - 1
        else:
            mom = float('nan')
        momentum.append(mom)
    df['momentum'] = momentum

    # 4. 因子打分（数值越好排名越前；PE/市值越小越好，动量越大越好）
    df = df.dropna(subset=['pe_ratio', 'market_cap', 'momentum'])
    df = df[df['pe_ratio'] > 0]  # 剔除负 PE

    df['rank_pe'] = df['pe_ratio'].rank(ascending=True)
    df['rank_cap'] = df['market_cap'].rank(ascending=True)
    df['rank_mom'] = df['momentum'].rank(ascending=False)

    df['score'] = (
        df['rank_pe'] * g.factor_pe_weight
        + df['rank_cap'] * g.factor_market_cap_weight
        + df['rank_mom'] * g.factor_momentum_weight
    )
    df = df.sort_values('score').head(g.hold_num)
    target_stocks = list(df['code'])

    # 5. 调仓：清掉不在 target 的，等权重买入新的
    cur_positions = list(context.portfolio.positions.keys())
    for stock in cur_positions:
        if stock not in target_stocks:
            order_target(stock, 0)

    if target_stocks:
        cash_per_stock = context.portfolio.total_value / len(target_stocks)
        for stock in target_stocks:
            order_target_value(stock, cash_per_stock)

    log.info('调仓完成，持仓：%s' % ', '.join(target_stocks))
