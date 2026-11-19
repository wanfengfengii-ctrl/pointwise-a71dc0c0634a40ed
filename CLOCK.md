# 站钟偏差交接

`README.md` 说明现有登记、观测修订、V1 站件、断源预测和报告领取。站钟件用于同一试验内的站钟有固定但未知偏差的情形。偏差以秒计，跨同站的各条读数保持不变。

## 调用入口

| 调用 | 返回 |
| --- | --- |
| `phase.station.issue.issue_clock(registry, observations, issues, trial_id, station, references, clock_bounds)` | 不可变站钟件，可读取其 `artifact_id` |
| `phase.station.artifact.encode_clock_artifact(artifact)` | 可交给中心的 JSON 文本 |
| `phase.analysis.intake.accept_clock(registry, catalog, payload, submitted)` | 已接纳的件号，`submitted` 沿用 `StationSource` |
| `phase.analysis.forecast.forecast_clock(registry, catalog, reports, artifact_ids, time)` | 已落账的 `PublishedReport` |

`clock_bounds` 为含两个端点的列表或元组，按下界、上界排列。数值输入沿用 V1 精确有理数口径，允许相等端点。`references` 沿用 `issue` 的明确修订规则。站钟件使用 JSON 对象，含整数 `version` 值 `2` 及字符串 `artifact_id`。件号绑定固定试验、站点、登记来源、明确修订、预算和证据。等价预算及同一固定内容重复签发沿用件号，接纳同内容重投返回原号，JSON 对象的字段顺序和空白无影响。坏件、来源不符及同号异内容均拒收，保留已有接纳结果。

站件交付名义时刻和固定校准证据。原观测台账与更正历史留站。证据须保全预算允许且实际时刻在登记时域内的全部整圈分枝。实际时刻等于名义时刻加本站钟差。读数使用实际时刻代入 V1 的模一相位规则。所有选中修订使用同一初相与频偏，同一试验同一站点的全部选中修订共用一个钟差，异站分别取值。同站多件的预算以有理端点比较，须一致。合计上限按各件所载修订引用计。

预测时刻在登记时域内，使用共同试验时基。输出仍为精确 `PhaseInterval` 元组，按 V1 顺序与开闭规则归并。合法输入无共同解释时签出带出处的空集，即使原因是预算内没有合法实际时刻。非法输入、坏件、未知件和混版选件抛出 `ValueError`，非法请求无新增成果。固定结果、选件出处和回执同次提交，写入失败可重试。使用原有 `phase.reports.export.read` 和 `export_report` 按号领取或导出存值，更正和重开后仍读原成果。原 V1 入口、编码、历史报告和回归继续可用。

## 对照样例

`clock_examples.py` 的 `CASES` 给出登记、读数、各件预算、预测时刻和按 `encode_phase_set` 表示的预期。`record_case` 通过原录入入口创建明确修订引用。以 `lifted_tick` 为例，预期的业务调用如下。连接及台账的创建见 README。

```python
from clock_examples import CASES, SOURCES, record_case
from phase.analysis.forecast import forecast_clock
from phase.analysis.intake import accept_clock
from phase.analysis.phase_set import encode_phase_set
from phase.station.artifact import encode_clock_artifact
from phase.station.issue import issue_clock
from phase.trials.stations import StationSource

case_id = 'lifted_tick'
trial, [(station, bounds, refs)] = record_case(case_id, registry, {'A': observations})
clock_piece = issue_clock(registry, observations, issues, trial, station, refs, bounds)
selected = accept_clock(registry, catalog, encode_clock_artifact(clock_piece),
                        StationSource(station, SOURCES[station]))
station_db.close()
report = forecast_clock(registry, catalog, reports, [selected], CASES[case_id]['forecast_at'])
assert encode_phase_set(report.phases) == CASES[case_id]['expected']
```

该例的名义时刻为 1 秒，读到 3/8 圈，频偏固定为 1/4 圈每秒。按固定 +1 秒钟差，实际时刻为 2 秒，初相是 7/8 圈。`python3 -B clock_examples.py` 运行原 V1 对照，打印名义成件的分枝上界与实算结果。`same_station` 中两份甲站件要求 1 秒内相差半圈，实际只能相差 1/4 圈，故应签空集。`separate_stations` 中两站分别允许自己的偏差，初相 3/4 圈可由甲站零秒偏差和乙站一秒偏差同时解释。

## 运行交付

沿用 `.pointwise-runtime.json` 的运行约定。`verify` 与 `demo` 是可执行的参数数组。核验运行原完整回归，并覆盖站钟件签发、接纳、断源预测、失败重试及固定领取，业务断言失败时返回非零状态。演示实际关闭站库后签发站钟报告，并在重开中心库后按号领取。双库关停及重开可参照 `tests/support.py`，回执提交失败可沿用 `tests/test_reports.py` 的延迟外键夹具。
