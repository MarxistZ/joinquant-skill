# =============================================================================
# 模板 04：股票横截面动量策略
# =============================================================================
# 适用场景：
#   - 中证 500 / 沪深 300 等指数成分股
#   - 周度调仓，过去 N 周涨幅前 K 名等权持有
#
# 经典文献：
#   - Jegadeesh & Titman (1993) 横截面动量
#   - 过去 6-12 月动量在中国 A 股表现一般，1-3 月反转更明显
# =============================================================================

import jqdata


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')
    set_slippage(FixedSlippage(0.02))

    g.universe_index = '000300.XSHG'
    g.lookback_weeks = 4
    g.hold_num = 20
    g.skip_recent_days = 3  # 跳过最近 N 天，避免短期反转

    # 周度调仓：每周一 09:31
    run_weekly(rebalance, weekday=1, time='09:31')


def rebalance(context):
    stocks = get_index_stocks(g.universe_index)

    momentum_scores = {}
    lookback_days = g.lookback_weeks * 5 + g.skip_recent_days

    for stock in stocks:
        prices = attribute_history(stock, lookback_days, '1d', ['close'])
        if len(prices) < lookback_days or prices['close'].iloc[0] <= 0:
            continue
        # 跳过最近 g.skip_recent_days 天的动量
        ret = prices['close'].iloc[-g.skip_recent_days - 1] / prices['close'].iloc[0] - 1
        momentum_scores[stock] = ret

    if not momentum_scores:
        log.warning('无动量数据')
        return

    # 排名前 hold_num
    sorted_stocks = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
    target_stocks = [s for s, _ in sorted_stocks[:g.hold_num]]

    # 调仓
    cur_positions = list(context.portfolio.positions.keys())
    for s in cur_positions:
        if s not in target_stocks:
            order_target(s, 0)

    if target_stocks:
        cash_per = context.portfolio.total_value / len(target_stocks)
        for s in target_stocks:
            order_target_value(s, cash_per)

    log.info('本周持仓 top %d，最高动量 %.2f%%' % (
        g.hold_num, sorted_stocks[0][1] * 100))
