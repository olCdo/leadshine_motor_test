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
