# Leadshine Motor Test

Leadshine LD2-CAN 电机测试工具。

当前阶段只完成 `Python` 项目骨架和 `CLI` 入口，不包含真实 `CANopen` / `PDO` 控制。

## 当前可验证命令

```powershell
python -m leadshine_motor_test --help
```

如未安装为 editable package，需临时设置 `PYTHONPATH=code` 后运行。
