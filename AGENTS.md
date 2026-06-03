# AGENTS.md

## 项目目的

本项目是面向 Leadshine LD2-CAN 伺服驱动器的 Python 电机测试工具。目标运行环境是 Orange Pi 5 Plus 上的 Ubuntu，Windows 仅用于代码编写和项目维护。

第一版目标是实现一个安全的 CLI 测试程序，通过 CANopen PDO 和 Profile Velocity Mode 控制单台电机。

## Markdown 写作规范

本项目所有 `.md` 文件统一采用中文为主的写法。

必须保留英文原文的内容包括：

- 技术名词：`Python`、`Ubuntu`、`SocketCAN`、`CANopen`、`PDO`、`SDO`、`NMT`、`Profile Velocity Mode`、`CLI`、`CSV`。
- CLI 命令：`enable`、`disable`、`speed <rpm>`、`stop`、`status`、`watch`、`quit`、`help`。
- CANopen 对象字典和字段：`6040 control word`、`6041 status word`、`60FF target velocity`、`606C actual velocity`、`pulses_per_rev` 等。
- 文件路径、配置字段、模块名、函数名、包名。

## 开发前必须阅读

每次开发前先阅读这些文件：

- `docs/requirements.md`
- `docs/technical_design.md`
- `docs/safety_guidelines.md`
- `docs/development_process.md`
- `docs/version_control.md`

`docs/` 中的本地 PDF 手册仅作为参考资料。PDF 手册被 git 忽略，禁止提交。

## 开发日志要求

每次开发步骤都必须更新：

- `dev_logs/development_log.md`：记录已完成事项、验证结果、发现的问题。
- `dev_logs/todo.md`：记录下一步计划、优先级、阻塞项和延期事项。

不要一次性修改大量无关内容。每一步开发都应该小、可验证、可单独提交。

## 安全要求

电机控制代码必须遵守 `docs/safety_guidelines.md`，尤其是：

- 使用保守的速度和加减速默认值。
- 拒绝超过配置限幅的 `speed <rpm>` 命令。
- `quit`、Ctrl+C 或异常退出时，先下发零速度，再断使能。
- 不自动执行 fault reset。
- 除非后续需求明确允许，否则不永久保存驱动器参数。

## 版本管理规则

遵守 `docs/version_control.md`。

提交必须小步推进。电机 PDF、运行日志、CSV 测试数据、虚拟环境、Python cache 文件都不能提交。
