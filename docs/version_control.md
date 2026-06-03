# 版本管理

## 分支

默认使用当前 `master` 分支，除非用户明确要求切换默认分支。

## 远程仓库

远程仓库：

```text
https://github.com/olCdo/leadshine_motor_test.git
```

## Commit 范围

使用小步 commit。每个 commit 应对应一个明确开发步骤。

首次 commit：

```text
chore: add project standards and development logs
```

首次 commit 只应包含：

- `AGENTS.md`
- `.gitignore`
- `docs/*.md`
- `dev_logs/*.md`

## Ignore 规则

不要提交：

- `docs/*.pdf`
- Python cache 文件。
- virtual environment。
- runtime logs。
- `CSV` 测试输出。
- 本地编辑器文件。

应提交：

- Markdown 项目标准。
- 开发日志。
- 源代码。
- 测试。
- 依赖声明文件。

## 提交前检查

每次 commit 前：

1. 运行相关验证。
2. 更新 `dev_logs/development_log.md`。
3. 更新 `dev_logs/todo.md`。
4. 运行 `git status --short`。
5. 确认 ignored 本地文件没有被 staged。
