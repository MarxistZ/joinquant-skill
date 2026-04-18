# =============================================================================
# 模板 01：单股票均线策略（聚宽入门模板）
# =============================================================================
# 适用场景：
#   - 第一次写聚宽策略，想快速跑通一个完整闭环
#   - 单股票 / 单 ETF 的趋势跟踪
#   - 5 日/20 日均线金叉买入、死叉卖出
#
# 直接使用方式：
#   1. 把整段代码复制粘贴到聚宽在线编辑器
#   2. 在编辑器里设置回测时间（建议 2018-01-01 至今）+ 初始资金（建议 100,000）
#   3. 点击「编译运行」即可
#
# 修改方向（按重要性排序）：
#   - g.security 改成你想跑的标的
#   - run_daily 的 time 参数（'open'=09:30 开盘价 / 'every_bar'=每根 bar / '14:50'=尾盘）
#   - MA 周期（短周期 / 长周期）
# =============================================================================

# 导入聚宽函数库
import jqdata


def initialize(context):
    """策略初始化函数，回测/模拟开始时只调用一次。"""

    # ----- 必备设置（5 项缺一不可）-----

    # 1. 基准指数（用于计算 alpha / beta）
    set_benchmark('000300.XSHG')

    # 2. 真实价格模式（动态复权）— 必开，否则有未来函数
    # RATIONALE: 传统前复权模式回测使用未来日期的复权因子，会产生回测高/实盘差的问题
    set_option('use_real_price', True)

    # 3. 输出日志级别
    log.set_level('order', 'error')

    # 4. 交易税费（券商手续费 + 印花税）
    # RATIONALE: 不设置则按聚宽默认值，可能与你的实际券商不一致
    set_order_cost(OrderCost(
        open_tax=0,                # 买入印花税：0
        close_tax=0.001,           # 卖出印花税：0.1%
        open_commission=0.0003,    # 买入手续费：万 3
        close_commission=0.0003,   # 卖出手续费：万 3
        close_today_commission=0,  # 平今手续费：股票为 0
        min_commission=5,          # 最低手续费：5 元
    ), type='stock')

    # 5. 滑点（模拟真实交易中的成交价偏差）
    # RATIONALE: 不设置则无滑点，回测过于乐观
    set_slippage(FixedSlippage(0.02))  # 固定滑点 0.02 元

    # ----- 策略参数（用 g.* 全局变量保存）-----
    g.security = '000001.XSHE'   # 平安银行（可改）
    g.short_period = 5            # 短周期均线
    g.long_period = 20            # 长周期均线

    # ----- 调度任务 -----
    # 每个交易日 09:30 调用一次 trade（开盘后）
    run_daily(trade, time='open')


def trade(context):
    """每日开盘时执行一次，判断信号、下单。"""

    # 取过去 long_period 天的收盘价
    # RATIONALE: 用 count 而不是 start_date / end_date，避免未来函数
    df = attribute_history(g.security, g.long_period, '1d', ['close'])

    if df is None or len(df) < g.long_period:
        log.info('数据不足 %d 天，跳过本日' % g.long_period)
        return

    short_ma = df['close'][-g.short_period:].mean()
    long_ma = df['close'].mean()
    cur_price = df['close'][-1]

    # 当前持仓
    cur_position = context.portfolio.positions.get(g.security)
    has_position = cur_position is not None and cur_position.total_amount > 0

    # 信号：金叉买入，死叉卖出
    if short_ma > long_ma and not has_position:
        # 满仓买入
        # RATIONALE: order_value 比 order 更安全，自动处理价格变动和手数取整
        order_value(g.security, context.portfolio.available_cash)
        log.info('[BUY] %s 短均 %.2f > 长均 %.2f，金叉买入' % (
            g.security, short_ma, long_ma))

    elif short_ma < long_ma and has_position:
        # 全部卖出
        # RATIONALE: order_target 设置目标持仓为 0，比 order(-amount) 更直观
        order_target(g.security, 0)
        log.info('[SELL] %s 短均 %.2f < 长均 %.2f，死叉卖出' % (
            g.security, short_ma, long_ma))

    # 记录每日信号到回测图表（最多 4 条线）
    record(short_ma=short_ma, long_ma=long_ma, price=cur_price)
