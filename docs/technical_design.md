# 技术设计

## 架构

程序应组织为一个小型 Python CLI 应用，模块边界保持清晰：

- `CLI` 命令循环。
- 配置和安全限幅。
- `CANopen` transport。
- `PDO mapping` 和 payload 编码。
- 驱动器状态与 telemetry 解码。
- `CSV logging`。

第一版避免过度抽象。代码应保持直接、可读，等真机行为验证后再扩展。

## CANopen 策略

在 Ubuntu 上通过 `python-can` 使用 `SocketCAN`。

第一版不依赖 EDS 文件，而是使用 Leadshine LD2-CAN 手册中确认的 object dictionary。

`SDO` 只用于启动和配置阶段。运行期控制和 telemetry 必须使用 `PDO`。

## 启动流程

1. 打开 CAN interface。
2. 按需要发送 `NMT reset/start`。
3. 进入 Pre-operational 状态，准备配置 `PDO`。
4. 通过 `SDO` 配置 `RPDO` 和 `TPDO` mapping。
5. 写入 `6060 = 3`，设置 `Profile Velocity Mode`。
6. 设置 acceleration 和 deceleration 参数。
7. 进入 Operational 状态。
8. 启动 `CLI` 命令循环和 telemetry 处理。

## 运行期 PDO 设计

### RPDO

`RPDO` 应携带：

- `6040 control word`。
- `60FF target velocity`。

`CLI` 接收 rpm，驱动器对象使用 pulse/s，因此按以下公式换算：

```text
pulse_per_second = rpm * pulses_per_rev / 60
```

默认 `pulses_per_rev` 为 `10000`。

### TPDO

`TPDO` 应返回：

- `6041 status word`。
- `606C actual velocity`。
- 母线电压。
- 温度。
- 实际转矩百分比。

如果驱动器无法把所有目标反馈项映射到选定的 `TPDO` 布局中，则 `6041 status word` 和 `606C actual velocity` 必须保留，缺失的 telemetry 记录到 `dev_logs/development_log.md`。

## 关键 Object Dictionary

- `6040 control word`。
- `6041 status word`。
- `6060 operation mode`。
- `6061 operation mode display`。
- `606C actual velocity`。
- `6077 actual torque`。
- `6079 bus voltage`。
- `6083 profile acceleration`。
- `6084 profile deceleration`。
- `60FF target velocity`。
- `5501:04 actual torque monitor`，作为实际转矩百分比的候选来源。
- `5502:06 temperature monitor`。

## 错误处理

- `SDO timeout` 视为启动失败。
- 长时间没有 `TPDO` 更新视为通信丢失。
- `6041 status word` 出现 fault bit 后，拒绝接受非零 `speed <rpm>`。
- 不自动执行 fault reset。
- 所有通信错误和驱动器状态错误都必须记录。
