# Log Generator

用于批量生成 Log Assistant 测试日志文件。

## 使用方式

```bash
python tools/log_generator/generate_logs.py
```

默认会在 `sample_logs/` 目录下生成 5 个 `.log` 文件，每个文件 120 行。

也可以指定数量和行数：

```bash
python tools/log_generator/generate_logs.py --files 10 --lines 300 --output sample_logs
```

生成的日志包含 `INFO`、`WARN`、`ERROR`、`DEBUG` 等级别，以及时间戳、服务名、请求 ID、用户 ID 和耗时字段，可直接通过前端上传测试。
