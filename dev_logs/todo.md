# 待办事项

## 下一步开发

1. 创建 `Python` 项目骨架。
   - 包结构。
   - `CLI` 入口。
   - 依赖声明。
   - 基础配置读取。
   - 本步骤不接入真实 CAN 控制。

2. 实现 `CANopen` 基础通信。
   - 打开 `SocketCAN` 总线。
   - 实现 `NMT reset/start` 命令。
   - 实现 expedited `SDO` read/write。
   - 实现基础 timeout 和错误处理。

3. 实现 `PDO` 配置和 payload 编解码。
   - 启动时临时配置 `RPDO` / `TPDO` mapping。
   - 实现 `RPDO` payload encoder。
   - 实现 `TPDO` payload decoder。
   - 为 payload 布局添加单元测试。

4. 实现速度模式控制。
   - `enable`
   - `disable`
   - `speed <rpm>`
   - `stop`
   - 保守速度和加减速限幅。

5. 实现状态监控和 `CSV` 日志。
   - 解析 `6041 status word`。
   - 读取实际速度。
   - 读取母线电压。
   - 读取温度。
   - 读取实际转矩百分比，作为负载参考。
   - 周期写入 `CSV` 日志。

## 当前阻塞项

- 真机测试前需要确认 Orange Pi 5 Plus 上的 CAN interface 名称、bitrate 和 node ID。
- 所有目标监控对象是否都能按预期映射到 `TPDO`，需要在驱动器上验证。

## 延期事项

- 多电机控制。
- Web UI。
- Windows mock mode。
- 永久保存驱动器参数。
- 外部 emergency stop、limit、brake IO 集成。
