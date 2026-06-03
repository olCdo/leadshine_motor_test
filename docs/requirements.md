# 需求说明

## 目标

构建一个安全的 Python CLI 电机测试程序，用于测试 Leadshine LD2-CAN 伺服驱动器。

程序运行在 Orange Pi 5 Plus 的 Ubuntu 环境中，通过 CANopen PDO 和 Profile Velocity Mode 控制单台电机。

## 已确认需求

- 开发语言：`Python`。
- 运行系统：`Ubuntu`。
- 开发系统：Windows 可用于代码编辑。
- 目标硬件：Orange Pi 5 Plus 连接 Leadshine LD2-CAN 驱动器。
- 通信方式：基于 `SocketCAN` 的 `CANopen`。
- 控制模式：`Profile Velocity Mode`。
- 运行期控制必须使用 `PDO`：
  - 设置目标速度，单位为 rpm。
  - 使能驱动器。
  - 断使能驱动器。
  - 停止电机。
- 运行期反馈必须使用 `PDO`：
  - 实际速度，单位为 rpm。
  - 母线电压。
  - 实际转矩百分比，作为负载 / 电流参考。
  - 是否使能。
  - 是否 fault。
  - 温度。
- 启动阶段允许使用 `SDO`：
  - 临时配置 `PDO mapping`。
  - 设置 operation mode。
  - 设置 acceleration 和 deceleration。
  - 执行基础启动检查。
- 测试运行时默认开启 `CSV logging`。

## 第一版范围

- 只控制单台电机。
- 只提供 `CLI` 交互。
- 只支持真实硬件。
- 保守默认值：
  - 最大速度：500 rpm。
  - acceleration：500 rpm/s。
  - deceleration：500 rpm/s。
  - `pulses_per_rev`：10000。
- 默认 CAN 设置：
  - interface：`can0`。
  - bitrate：`1000000`。
  - node ID：`1`。

## 第一版不做

- 多电机控制。
- 多轴同步控制。
- Web UI。
- Windows 本地 mock mode。
- 永久保存驱动器参数。
- 自动执行 fault reset。
- 直接管理外部 emergency stop、limit 或 brake IO。

## CLI 命令

第一版 `CLI` 需要提供：

- `enable`
- `disable`
- `speed <rpm>`
- `stop`
- `status`
- `watch [interval_seconds]`
- `quit`
- `help`
