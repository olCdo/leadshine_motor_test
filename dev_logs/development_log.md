# 开发日志

## 2026-06-03

### 已完成

- 初始化 git 仓库，并配置远程仓库 `origin` 为 `https://github.com/olCdo/leadshine_motor_test.git`。
- 确认项目方向：
  - 使用 `Python`。
  - 目标运行环境为 Orange Pi 5 Plus 上的 `Ubuntu`。
  - 目标驱动器为 Leadshine LD2-CAN。
  - 使用 `CANopen Profile Velocity Mode`。
  - 运行期控制使用 `PDO`。
  - 第一版只控制单台电机。
- 创建项目治理文档和版本管理规则。
- 添加 `.gitignore`，确保本地 PDF 手册不进入 git。
- 将所有 `.md` 文件统一调整为中文为主，保留技术名词、CLI 命令、CANopen 对象字典和配置字段英文原文。

### 验证

- 确认仓库首次提交已完成。
- 确认本地手册存在于 `docs/LD2-CAN系列用户使用手册V2.1.pdf`。
- 确认手册 PDF 被 `.gitignore` 中的 `docs/*.pdf` 忽略。
- 确认项目标准文档、开发日志和待办文件均采用中文表达。

### 问题 / 备注

- 尚未实现任何电机控制代码。
- Orange Pi 5 Plus 的 Ubuntu CAN 硬件配置不属于当前仓库第一阶段范围，真机测试前需要单独确认。
- 目标监控项能否全部稳定映射到 `TPDO`，需要后续真机集成时验证。

## 2026-06-03 - Python 项目骨架

### 已完成

- 创建 `Python` 项目骨架。
- 新增 `pyproject.toml`，声明包路径、版本和 `leadshine-motor-test` console script。
- 新增 `code/leadshine_motor_test/` 包目录。
- 新增 `CLI` 入口，支持 `--help`、`--version`、`--show-config` 和基础配置参数。
- 新增 `AppConfig`，集中保存默认 `SocketCAN`、node ID、速度限幅和 `pulses_per_rev`。
- 新增最小 `unittest`，覆盖配置校验和 `CLI` 参数解析。
- 新增 `README.md`，说明当前阶段的可验证命令。

### 验证

- 运行 `$env:PYTHONPATH='code'; python -m leadshine_motor_test --help`，通过。
- 运行 `$env:PYTHONPATH='code'; python -m leadshine_motor_test --show-config`，通过。
- 运行 `$env:PYTHONPATH='code'; python -m unittest discover -s tests`，3 个测试通过。
- 运行 `$env:PYTHONPATH='code'; python -m compileall -q code tests`，通过。

### 问题 / 备注

- 本步骤没有接入真实 CAN，也没有实现 `CANopen`、`SDO` 或 `PDO`。
- 下一步应实现 `CANopen` 基础通信，并继续避免真实电机运动。

## 2026-06-03 - Orange Pi 测试流程要求

### 已完成

- 明确后续每个可测试开发步骤完成后，需要 push 到远程仓库，方便 Orange Pi 拉取。
- 在 `AGENTS.md`、`docs/development_process.md`、`docs/version_control.md` 和 `README.md` 中补充 Orange Pi 拉取和测试说明要求。

### 验证

- 待提交后执行 `git status --short --ignored`。
- 待 push 后确认远程仓库包含当前测试代码。

### 问题 / 备注

- 当前可测试内容仍然只是 `CLI` 骨架，不需要连接电机，也不会访问 CAN。
