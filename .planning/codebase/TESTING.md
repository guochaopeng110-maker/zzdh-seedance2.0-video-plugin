# 测试 - 测试结构

## 测试框架
- 未发现明确的测试框架 (如 pytest, unittest)
- 在宿主应用程序中通过执行插件进行手动测试

## 测试方法
- 视频生成软件内的进程内测试
- 针对 API 请求/响应的使用 print 的调试
- 用于追踪生成结果的任务日志数据库

## 手动测试模式
```python
# 开发期间的调试输出
print(f"请求端点: {endpoint}")
print(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)[:800]}")
print(f"API 响应: {result}")
```

## 覆盖范围
- API 身份验证 (Bearer 令牌)
- 每个模型的请求 Payload 构建
- 状态轮询循环
- 视频下载
- 错误处理和重试逻辑
- 参数清洗

## Mock (模拟)
- 未检测到 Mock 框架
- 集成测试需要真实的 API 测试

## 质量保证
- 用于结果追踪的 SQLite 任务日志
- 辅助重试决策的错误关键字过滤
- 用于插件更新的 SHA256 验证
