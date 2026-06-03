# Leadshine Motor Test

Leadshine LD2-CAN 电机测试工具。

当前阶段只完成 `Python` 项目骨架和 `CLI` 入口，不包含真实 `CANopen` / `PDO` 控制。

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

当前代码的离线检查不需要连接 CAN。后续接入 `SocketCAN` 时会使用 `python-can`。

## 当前可验证命令

```powershell
python -m leadshine_motor_test --help
```

如未安装为 editable package，需临时设置 `PYTHONPATH=code` 后运行。

## Orange Pi 拉取与测试

首次拉取：

```bash
git clone https://github.com/olCdo/leadshine_motor_test.git
cd leadshine_motor_test
```

已有仓库时更新：

```bash
cd leadshine_motor_test
git pull
```

当前阶段离线测试不连接电机，也不会访问 CAN：

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=code python3 -m leadshine_motor_test --help
PYTHONPATH=code python3 -m leadshine_motor_test --show-config
PYTHONPATH=code python3 -m leadshine_motor_test --check-canopen-codecs
PYTHONPATH=code python3 -m leadshine_motor_test --check-pdo-codecs
PYTHONPATH=code python3 -m leadshine_motor_test --check-drive-codecs
```

`--check-canopen-codecs` 只做离线 `CANopen` NMT / SDO 编码检查，不打开 `can0`，不会让电机运动。

`--check-pdo-codecs` 只做离线 `PDO mapping` 和 payload 编解码检查，不打开 `can0`，不会让电机运动。

`--check-drive-codecs` 只做离线状态字解析、控制字序列和速度限幅检查，不打开 `can0`，不会让电机运动。

## Orange Pi 通信测试

通信测试会打开 `can0`，并通过 `SDO` 读取 `6041 status word`。

它不会写 `6040 control word`，不会设置 `60FF target velocity`，不会使能驱动器，也不会让电机运动。

先确认 `can0` 已存在并处于正确 bitrate：

```bash
ip link show can0
```

如需配置 `can0` 为 1 Mbps：

```bash
sudo ip link set can0 down || true
sudo ip link set can0 up type can bitrate 1000000
```

执行通信测试：

```bash
PYTHONPATH=code python3 -m leadshine_motor_test --check-canopen-comm --interface can0 --node-id 1
```

通过时会看到：

```text
result=ok
status_word=0x....
```

## Orange Pi PDO mapping 配置测试

这个测试会通过 `SDO` 临时写入 `RPDO1` / `TPDO1` mapping。

它不会写 `6040 control word`，不会设置 `60FF target velocity`，不会使能驱动器，也不会让电机运动。它也不会保存参数到驱动器，断电后驱动器会回到原有持久配置。

```bash
PYTHONPATH=code python3 -m leadshine_motor_test --configure-pdo-mapping --interface can0 --node-id 1
```

通过时会看到：

```text
result=ok
rpdo1_cob_id=0x201
tpdo1_cob_id=0x181
rpdo1_mapping=0x60400010,0x60FF0020
tpdo1_mapping=0x60410010,0x606C0020
```

## Orange Pi 速度模式准备测试

这个测试会通过 `SDO` 临时配置 `PDO mapping`，设置 `6060 operation mode = 3`，设置 `6083/6084` 加减速，并把 `60FF target velocity` 写为 0。

它不会写 `6040 control word`，不会使能驱动器，也不会让电机运动。它也不会保存参数到驱动器。

```bash
PYTHONPATH=code python3 -m leadshine_motor_test --prepare-velocity-mode --interface can0 --node-id 1
```

通过时会看到：

```text
result=ok
mode_display=3
status_word=0x....
state=...
```
