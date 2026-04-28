# Demo Data

创建一个可展示的演示账号和日志数据。

```bash
docker compose exec api python tools/demo_data/seed_demo_data.py
```

演示账号：

- 邮箱：`demo@example.com`
- 密码：`demo12345`

脚本会重置这个演示账号，并写入一份已分析的结账链路故障日志。
