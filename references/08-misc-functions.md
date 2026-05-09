# 08 — 其他函数

> 画图、日志、文件读写、消息推送、代码转换、性能分析等辅助工具。

## record ★ 画图函数

```python
record(**kwargs)
```

回测/模拟专用。在回测图表上画出额外曲线（收益曲线和基准曲线是自动画的）。

**参数**：一个或多个 `key=value`，key 为曲线名称，value 为数值（不能是列表）

**返回值**：None

**注意**：
- 按天展示，分钟回测取当天最后一次 `record` 的值
- 以 16:00 为界，之后绘制的属于第二天
- 需从回测开始就调用，不支持中间时段开始调用

```python
def handle_data(context, data):
    d = data['000001.XSHE']
    record(price=d.price, open=d.open, close=d.close)
    record(price=100)  # 画一条值为100的直线
```

---

## log 日志

```python
log.error(content)
log.warn(content)
log.info(content)
log.debug(content)
print(content1, content2, ...)  # 等同于 log.info，但每个元素占一行
```

### log.set_level 设定日志级别

```python
log.set_level(name, level)
```

**name** 取值：
- `'order'`：order 系列 API 产生的日志
- `'history'`：history/attribute_history/get_price 产生的日志
- `'strategy'`：策略代码中的自定义日志
- `'system'`：系统日志（除以上三类外的日志）

**level** 取值（级别递增）：`'debug'` < `'info'` < `'warning'` < `'error'`

```python
log.set_level('order', 'info')
```

建议保持默认 `debug` 级别，便于排查问题。模拟交易中如需修改，在 `after_code_changed` 中重新设置。

---

## send_message 发送微信消息

```python
send_message(message, channel='weixin')
```

**仅模拟交易可用**，回测中调用会被忽略，无任何提示。

**返回值**：True/False，失败时日志显示错误信息。

**限制**：
- 需绑定并开启微信通知
- 每个账号每天最多 5 条自定义消息（可用积分兑换更多）
- 消息长度 ≤ 200 字符，不能包含回车/换行
- 与下单通知不同：下单通知每天最多 60 条，且需开启对应模拟交易的通知开关

```python
send_message('美好的一天~')
```

---

## write_file 写文件

```python
write_file(path, content, append=False)
```

将回测/模拟交易数据写入聚宽研究环境的私有空间。

**参数**：
- `path`：相对路径（相对于研究根目录）
- `content`：文件内容（str/unicode/二进制）
- `append`：追加模式，默认 `False`（清除原内容）

```python
write_file('test.txt', 'hello world')

import json
write_file('HS300.stocks.json', json.dumps(get_index_stocks('000300.XSHG')))

df = attribute_history('000001.XSHE', 5, '1d')
write_file('df.csv', df.to_csv(), append=False)
```

写入失败一般因路径不合法，会抛出异常。

---

## read_file 读文件

```python
read_file(path)
```

在回测/模拟交易中读取研究环境的私有文件。返回原始内容（bytes），不做 decode。

```python
# 解析 JSON
import json
content = read_file('HS300.stocks.json')
securities = json.loads(content)

# Python 3 解析 CSV
import pandas as pd
from six import BytesIO
body = read_file('open.csv')
data = pd.read_csv(BytesIO(body))
```

**注意**：不能读取本地文件，需先上传到聚宽研究环境。支持 csv、excel、json 等格式。

---

## 自定义 Python 库

将 `.py` 文件放在研究根目录，策略中直接 `import`：

```python
# 研究根目录/mylib.py
# -*- coding: utf-8 -*-
from kuanke.user_space_api import *
my_stocks = get_index_stocks('000300.XSHG')

# 策略代码中
from mylib import *
def initialize(context):
    log.info(my_stocks)
```

暂时只支持根目录的 `.py` 文件，不支持子目录。含中文需加 `# -*- coding: utf-8 -*-`。

---

## normalize_code 代码转换

```python
normalize_code(code)
```

将其他格式的股票代码转为聚宽格式。支持 A 股、期货、场内基金。支持字符串、int、list 或 tuple。

```python
codes = ('000001', 'SZ000001', '000001SZ', '000001.sz', '000001.XSHE')
print(normalize_code(codes))
# ['000001.XSHE', '000001.XSHE', '000001.XSHE', '000001.XSHE', '000001.XSHE']
```

---

## enable_profile 性能分析

```python
enable_profile()
```

回测专用。在所有代码最上方调用，点击"运行回测"后在结果页看到性能分析（行级耗时）。

**注意**：
- 本身会影响性能，不需要时不要调用
- 耗时长的回测建议先分析短周期（如一周）

---

## create_backtest 研究中创建回测

```python
create_backtest(
    algorithm_id, start_date, end_date,
    frequency='day', initial_cash=10000,
    initial_positions=None, extras=None,
    name=None, code='', benchmark=None,
    python_version=2, use_credit=False
)
```

只能在研究中使用。返回一个字符串即 `backtest_id`。

**关键参数**：
- `extras`：dict，值会在 `initialize` 执行后覆盖 `g` 变量
- `initial_positions`：初始持仓，格式见下方示例
- `code`：直接传入策略代码字符串创建回测（覆盖原策略代码）
- `benchmark`：覆盖原策略的基准，默认None表示沿用原策略设置
- `use_credit`：是否允许消耗积分新建回测，默认 `False`；日编译/回测超过免费时间后，每 30 分钟消耗 2 积分。注意，对于已在运行中的回测，此配置不生效。
- `python_version`：已废弃，目前只支持 Python 3

```python
algorithm_id = "xxxx"
params = {
    "algorithm_id": algorithm_id,
    "start_date": "2015-10-01",
    "end_date": "2016-07-31",
    "frequency": "day",
    "initial_cash": "1000000",
    "initial_positions": [
        {'security': '000001.XSHE', 'amount': '100'},
        {'security': '000063.XSHE', 'amount': '100', 'avg_cost': '1.0'},
    ],
    "extras": {'a': 1, 'b': 2},
}
created_bt_id = create_backtest(**params)
```

---

## get_backtest 研究中获取回测与模拟交易信息

```python
gt = get_backtest(backtest_id)
```

只能在研究中使用。返回对象方法：

| 方法 | 说明 |
|------|------|
| `gt.get_status()` | 回测状态：none/running/done/failed/canceled/paused/deleted |
| `gt.get_params()` | 回测参数（dict） |
| `gt.get_results()` | 收益曲线（list of dict） |
| `gt.get_positions(start_date=None, end_date=None)` | 持仓详情，可选起止日期 |
| `gt.get_orders(start_date=None, end_date=None)` | 交易详情，可选起止日期 |
| `gt.get_records()` | `record()` 记录 |
| `gt.get_risk()` | 总风险指标 |
| `gt.get_period_risks()` | 分月风险指标 |
| `gt.get_balances(start_date=None, end_date=None)` | 每日市值，可选起止日期 |

---

## 常见失败模式

| 错误用法 | 问题 |
|----------|------|
| `record(price=[1,2,3])` | value 不能是列表，只能是单个数值 |
| 回测中调 `send_message` | 只在模拟交易生效，回测静默忽略 |
| `read_file('/home/user/data.csv')` | 只能读研究根目录的相对路径 |
| `log.set_level('all', 'info')` | name 必须是 `'order'`/`'history'`/`'strategy'`/`'system'` |
| `normalize_code('600001')` 期望港股 | 仅支持 A 股、期货、场内基金 |
| `create_backtest(..., use_credit=False)` 时积分不足 | 回测超时后会被终止，需设为 `True` |
