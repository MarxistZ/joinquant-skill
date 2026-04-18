# =============================================================================
# 模板 05：均值回归策略（布林带 + RSI）
# =============================================================================
# 适用场景：
#   - 单股票或 ETF 的均值回归交易
#   - 高波动 / 区间震荡市场
#
# 信号：
#   - 价格触碰布林带下轨 + RSI < 30 → 买入
#   - 价格触碰布林带上轨 + RSI > 70 → 卖出
#   - 中轨止盈
# =============================================================================

import jqdata
import numpy as np


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(FixedSlippage(0.02))

    g.security = '510300.XSHG'  # 沪深 300 ETF（默认）
    g.boll_period = 20           # 布林带周期
    g.boll_std = 2               # 标准差倍数
    g.rsi_period = 14
    g.rsi_oversold = 30
    g.rsi_overbought = 70

    run_daily(trade, time='14:50')  # 尾盘交易


def calc_rsi(prices, period):
    """计算 RSI。聚宽自带 talib 等库，但这里手算示范。"""
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices)
    gains = deltas.clip(min=0)
    losses = -deltas.clip(max=0)
    avg_gain = gains[-period:].mean()
    avg_loss = losses[-period:].mean()
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def trade(context):
    df = attribute_history(g.security, g.boll_period + g.rsi_period, '1d', ['close'])
    if len(df) < g.boll_period + 1:
        return

    closes = df['close'].values
    cur = closes[-1]

    # 布林带
    window = closes[-g.boll_period:]
    mid = window.mean()
    std = window.std(ddof=0)
    upper = mid + g.boll_std * std
    lower = mid - g.boll_std * std

    rsi = calc_rsi(closes, g.rsi_period)
    if rsi is None:
        return

    cur_position = context.portfolio.positions.get(g.security)
    has_position = cur_position is not None and cur_position.total_amount > 0

    record(price=cur, upper=upper, lower=lower, mid=mid)

    # 买入
    if not has_position and cur <= lower and rsi <= g.rsi_oversold:
        order_value(g.security, context.portfolio.available_cash)
        log.info('[BUY] price=%.2f, lower=%.2f, RSI=%.1f' % (cur, lower, rsi))

    # 卖出（极端超买）
    elif has_position and cur >= upper and rsi >= g.rsi_overbought:
        order_target(g.security, 0)
        log.info('[SELL] price=%.2f, upper=%.2f, RSI=%.1f' % (cur, upper, rsi))

    # 止盈（回到中轨且有盈利）
    elif has_position and cur >= mid and cur_position.avg_cost > 0:
        if cur > cur_position.avg_cost * 1.05:  # 至少 5% 盈利
            order_target(g.security, 0)
            log.info('[TAKE PROFIT] price=%.2f, avg_cost=%.2f' % (cur, cur_position.avg_cost))
