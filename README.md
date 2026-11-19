# 旋转检具频闪复核 V1

精密量具厂的两站量测员从频闪读数单录入相位闭弧。站端按指定修订签发固定件，夜班关站库后凭中心已收站件复核可达相位，次班按报告号核查签发时的结果和出处。

## 一天的工作

1. 质控员用试验工单号登记检具、站点来源、时域和频偏预算，形成固定参数快照。
2. 量测员录入观测号、原时刻和沿增相方向的闭弧，站库记下首修订。
3. 抄录有误时，以当前父修订追加更正。原读数及修订号仍可查。
4. 量测员按明确修订签发本站 V1 站件。站件绑定试验、登记来源、修订引用和可独立解释的校准证据。原读数及更正历史留站。
5. 夜班将件录入独立中心库，核对登记来源和件号绑定，然后可关闭各站库。
6. 分析员选件并指定预测时刻，中心计算同一次校准能产生的全部相位，将结论及回执一起签发。
7. 次班按报告号领取或导出原结论和原选件出处。更正读数后可凭新站件另发报告。

## 安装与运行

使用 Python 3.11 标准库及其 SQLite。项目根目录下运行完整回归和演示。

```sh
python3 -B check_project.py
python3 -B demo.py
```

回归入口由运行平台提供，原套件位于 `tests/`。演示读取 `example.json`，在隔离临时目录建立中心库及两站库，真正关闭站库后做预测，再重开中心库读取。普通场景在频偏固定为零时对两闭弧求共同值，结果是 `[1/4,3/8]`。另一场景在 0 秒观测 `3/4→1/4`、1 秒观测精确的零线，频偏为 `[0,1/4]` 时，2 秒可能相位为 `[0,1/4]`。

## Python 接口

用 `phase.storage.connect(path)` 打开 SQLite 连接。中心连接可承载登记、目录和报告三个台账。每站用自己的连接承载观测与签发台账。调用者负责关闭连接。台账构造时创建缺少的表，重复构造及重开保留已有数据。写入入口拥有自己的事务。

```python
from phase.trials.registry import TrialRegistry, register
from phase.trials.stations import StationSource
from phase.observations.ledger import ObservationLedger
from phase.observations.intake import record_arc, correct
from phase.station.ledger import StationLedger
from phase.station.issue import issue
from phase.station.artifact import encode_artifact
from phase.analysis.catalog import AcceptedCatalog
from phase.analysis.intake import accept
from phase.analysis.forecast import forecast
from phase.reports.ledger import ReportLedger
from phase.reports.export import read, export_report

registry = TrialRegistry(center_db)
catalog = AcceptedCatalog(center_db)
reports = ReportLedger(center_db)
observations = ObservationLedger(east_db)
issued = StationLedger(east_db)
trial = register(registry, 'work-17', 'gauge-2', {'east': 'east-desk', 'west': 'west-desk'},
                 (0, 4), (0, '1/4'))
old = record_arc(registry, observations, trial, 'east', 'flash-1', 0, '3/4', '1/4')
new = correct(registry, observations, old.ref.key, old.ref, 0, '7/8', '1/4')
package = issue(registry, observations, issued, trial, 'east', [old.ref])
received = accept(registry, catalog, encode_artifact(package), StationSource('east', 'east-desk'))
east_db.close()
result = forecast(registry, catalog, reports, [received], '2')
assert read(reports, result.report_id) == result
payload = export_report(reports, result.report_id)
```

`register` 返回登记工单号，工单号在共同登记目录内唯一，登记完成后参数固定。`record_arc` 和 `correct` 返回不可变修订，`ref` 可用于成件或按修订读取。`issue` 返回不可变站件。同站对同一有序归档内容重复签发会返回同一件号。`accept` 接收 V1 JSON 文本及登记来源，返回件号。同号同内容可重交，异件拒绝覆盖。来源核对基于试验内的站点与交接来源对应关系。

`forecast` 接收非空的一组不同件号，按各件所载的修订引用计数，最多六条。`PublishedReport` 包含报告号、试验号、预测时刻、相位集合、按件号排序的出处和回执。`read` 返回固定报告，`export_report` 返回其规范 JSON 文本，有效但未知的报告号得到 `None`。错误参数和业务拒绝抛出 `ValueError`，SQLite 提交错误向调用者传递。成功报告和回执在一次提交后才返回。

## 数值约定

时刻以秒计，登记时域在 `[0,4]` 内。频偏以圈每秒计，登记闭区间在 `[−1/4,1/4]` 内。数值输入接受 `Fraction`、整数和有理数字符串，存档使用约分后的规范字符串。观测端点均在 `[0,1)`，起点大于终点表示过零，起终点相等表示刻线。缺项与越界数值均为输入错误。

初相 `p` 在 `[0,1)`，频偏 `d` 在登记闭区间。时刻 `t` 的读数是 `(p + t*d) mod 1`。站件表达所选修订共同允许的校准值，中心要求同一对 `p,d` 满足全部固定件后再投影。输出按 `[0,1)` 坐标升序，以精确有理数和端点开闭标志保留每个分量。跨零在 0 处分开，1 可作为开放上端点。无共同校准时签发带出处的空集。计算、排序与手算样例均是确定性的。
