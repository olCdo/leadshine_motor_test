# 安全规范

## 默认安全策略

第一版是测试工具，不是生产级 motion controller。程序必须优先采用保守行为。

默认值：

- 最大速度：500 rpm。
- acceleration：500 rpm/s。
- deceleration：500 rpm/s。
- 只控制单台电机。
- 不自动执行 fault reset。
- 不永久保存驱动器参数。

## 命令安全

- 驱动器报告 fault 时，拒绝非零 `speed <rpm>`。
- 当速度绝对值超过配置的 max rpm 时，拒绝执行。
- `stop` 必须下发零 `target velocity`。
- `disable` 必须先下发零 `target velocity`，再断使能。
- `quit`、Ctrl+C 和异常退出时，应尝试：
  1. 下发零 `target velocity`。
  2. 短暂等待。
  3. 断使能驱动器。

## Fault 处理

驱动器报告 fault 时：

- 不自动复位。
- 停止接受非零 `speed <rpm>`。
- 在 `CLI` 中清晰显示 fault 状态。
- 在 `CSV` 日志中记录 fault 状态。

后续只有在测试流程确认后，才允许增加显式的人工 fault reset 命令。

## 外部安全

第一版不管理外部 emergency stop、limit 或 brake IO。

电机运动前，测试台必须具备合适的物理安全条件：

- 电机固定可靠。
- 负载安全，或处于无负载测试条件。
- emergency stop 可触达。
- 接线和接地正确。
- CAN termination 和 bitrate 正确。

## 参数安全

第一版不永久保存参数到驱动器。

`PDO mapping` 和运行参数应在程序启动时临时配置，使驱动器断电重启后能够回到原有持久配置。
