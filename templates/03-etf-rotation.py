# =============================================================================
# 模板 03：ETF 轮动策略
# =============================================================================
# 适用场景：
#   - 在多个行业 / 主题 ETF 之间动量轮动
#   - 每月初买入过去 N 天涨幅最大的 K 个 ETF
#
# 经典思路（来源动量因子文献）：
#   - 计算每个 ETF 过去 20/60 日累计收益
#   - 排名前 K 等权持有
#   - 月度再平衡
# =============================================================================

import jqdata


def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(
        open_tax=0, close_tax=0.001,
        open_commission=0.0003, close_commission=0.0003,
        close_today_commission=0, min_commission=5,
    ), type='stock')  # ETF 也按 stock 类型计算
    set_slippage(FixedSlippage(0.001))  # ETF 流动性好，滑点更小

    # 策略参数
    g.etf_pool = [
        '510300.XSHG',  # 沪深 300 ETF
        '510500.XSHG',  # 中证 500 ETF
        '512100.XSHG',  # 中证 1000 ETF
        '513100.XSHG',  # 纳指 ETF
        '513050.XSHG',  # 中概互联
        '518880.XSHG',  # 黄金 ETF
        '512880.XSHG',  # 证券 ETF
        '512200.XSHG',  # 房地产 ETF
        '512170.XSHG',  # 医疗 ETF
        '515030.XSHG',  # 新能源车
    ]
    g.lookback_days = 20  # 动量计算窗口
    g.top_k = 3            # 持有前 K 个

    run_monthly(rebalance, monthday=1, time='09:31')


def rebalance(context):
    """月度调仓。"""

    momentum = {}
    for etf in g.etf_pool:
        prices = attribute_history(etf, g.lookback_days + 1, '1d', ['close'])
        if len(prices) < g.lookback_days + 1 or prices['close'].iloc[0] <= 0:
            continue
        # 累计收益率
        ret = prices['close'].iloc[-1] / prices['close'].iloc[0] - 1
        momentum[etf] = ret

    if not momentum:
        log.warning('无 ETF 动量数据，跳过')
        return

    # 排名取 top K
    sorted_etfs = sorted(momentum.items(), key=lambda x: x[1], reverse=True)
    top_etfs = [etf for etf, _ in sorted_etfs[:g.top_k]]
    log.info('动量排名：%s' % ', '.join([
        '%s(%.2f%%)' % (etf, mom * 100) for etf, mom in sorted_etfs[:g.top_k]
    ]))

    # 卖掉不在 top K 的
    cur_positions = list(context.portfolio.positions.keys())
    for etf in cur_positions:
        if etf not in top_etfs:
            order_target(etf, 0)

    # 等权重买入 top K
    if top_etfs:
        cash_per = context.portfolio.total_value / len(top_etfs)
        for etf in top_etfs:
            order_target_value(etf, cash_per)
