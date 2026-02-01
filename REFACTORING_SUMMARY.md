# 架构重构总结 - ccBot v1.1

## 🎯 重构目标

解决原有架构的Session管理问题和频繁的timeout错误。

## 🔍 原有架构问题

### 问题1: Session与Runner不匹配
- **SessionManager**: 每个用户可以有多个Session
- **RunnerManager**: 每个用户只有一个Runner进程
- **结果**: 多个Session共享同一个Claude CLI进程，一个卡住影响全部

### 问题2: 频繁Timeout
- 进程状态管理不当
- 缺少健康检查机制
- 超时时间设置过短（60秒）
- 没有自动恢复机制

### 问题3: 资源管理缺失
- 没有进程清理机制
- 缺少资源限制
- 僵死进程无法自动清理

## ✅ 重构内容

### 1. Session-Runner一对一架构

**改变**:
```python
# 旧架构
RunnerManager._runners: Dict[int, ClaudeRunner]  # user_id -> runner

# 新架构
RunnerManager._runners: Dict[str, ClaudeRunner]  # session_id -> runner
```

**优势**:
- ✅ Session隔离：每个Session独立进程
- ✅ 故障隔离：一个Session卡住不影响其他
- ✅ 并发能力：可同时处理多个Session
- ✅ 更好的调试：每个Session有独立的日志和状态

### 2. 健康检查与自动恢复

**新增功能**:
```python
class ClaudeRunner:
    async def health_check(self) -> bool
    async def ensure_healthy(self) -> bool
    async def restart(self)
```

**检查项**:
- ✅ 进程是否存活
- ✅ 是否卡在RUNNING状态
- ✅ 响应队列是否过大
- ✅ 超时自动重启

### 3. 资源管理与限制

**新增功能**:
```python
class RunnerManager:
    async def start_cleanup_task()      # 启动自动清理
    async def cleanup_idle_runners()    # 清理僵死进程
    def get_user_session_count()        # 获取用户Session数
```

**限制**:
- ✅ 每用户最大5个并发Session（可配置）
- ✅ 每5分钟自动清理僵死进程
- ✅ 超过30分钟无活动自动清理

### 4. 超时配置优化

**改进**:
- ⏰ 超时时间：60秒 → 600秒（10分钟）
- 📊 可配置：通过环境变量 `CLAUDE_TIMEOUT`
- 🔄 使用配置值而非硬编码

### 5. 代码优化

**handlers.py 改进**:
- 新增 `get_or_create_runner()` 辅助函数
- 统一的Session-Runner获取逻辑
- 更好的错误处理和提示
- 所有命令支持Session上下文

## 📊 改进对比

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| Session隔离 | ❌ 共享进程 | ✅ 独立进程 |
| 并发处理 | ❌ 单进程串行 | ✅ 多进程并发 |
| 故障隔离 | ❌ 一个卡住全卡 | ✅ 独立故障 |
| 健康检查 | ❌ 无 | ✅ 自动检查 |
| 自动恢复 | ❌ 无 | ✅ 自动重启 |
| 资源清理 | ❌ 手动 | ✅ 自动定期清理 |
| 超时时间 | ⏰ 60秒 | ⏰ 600秒 |
| Session限制 | ❌ 无限制 | ✅ 每用户5个 |

## 🚀 使用建议

### 1. 配置优化

编辑 `.env` 文件：

```bash
# 超时时间（根据网络情况调整）
CLAUDE_TIMEOUT=600

# 每用户最大并发Session
MAX_CONCURRENT_SESSIONS=5

# Session超时时间（分钟）
SESSION_TIMEOUT_MINUTES=120
```

### 2. 监控

使用新增的状态命令：

```bash
/status  # 查看当前Session和Runner状态
/stats   # 查看使用统计
```

### 3. 故障排查

如果遇到问题：

1. 检查Runner状态：`/status`
2. 停止当前Session：`/stop`
3. 结束并重新开始：`/end` + `/new`
4. 查看日志了解详细错误

### 4. 资源管理

- 不用的Session及时用 `/end` 结束
- 系统会自动清理30分钟无活动的Session
- 达到Session上限时会提示，需要结束旧Session

## 🔧 技术细节

### Runner生命周期

```
创建Session → 首次消息时创建Runner → 处理请求
    ↓
健康检查（每次请求前）
    ↓
    有问题？→ 自动重启
    ↓
    正常处理
    ↓
长时间无活动（30分钟）→ 自动清理
```

### 清理策略

- **定时清理**: 每5分钟执行一次
- **清理条件**:
  - 进程已退出
  - 超过30分钟无活动
  - 健康检查持续失败

## 📝 迁移说明

### 对现有用户的影响

✅ **向后兼容**: 现有Session自动迁移
✅ **无需改变**: 使用方式完全一致
✅ **性能提升**: 响应更快，更稳定

### 首次启动后

1. 现有Session会继续工作
2. 新消息会自动创建对应的Runner
3. 旧的Runner会在30分钟后自动清理

## 🎉 预期效果

1. **Timeout大幅减少**:
   - 超时时间从60秒增加到600秒
   - 卡住的Session不会影响其他Session

2. **稳定性提升**:
   - 自动健康检查和恢复
   - 僵死进程自动清理

3. **并发能力**:
   - 可以同时处理多个Session
   - 每个用户最多5个并发Session

4. **资源优化**:
   - 自动清理闲置资源
   - 防止资源耗尽

## 🔍 故障排查

### 如果仍然遇到Timeout

1. **检查网络**: Claude API可能响应慢
   ```bash
   # 尝试切换到API Provider
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your_key
   ```

2. **增加超时**:
   ```bash
   CLAUDE_TIMEOUT=900  # 15分钟
   ```

3. **查看日志**:
   ```bash
   # 日志会显示详细的超时原因
   tail -f logs/ccbot.log
   ```

### 如果达到Session限制

```bash
# 查看当前Session
/sessions

# 结束不需要的Session
/end
```

## 📚 相关文件

- `backend/claude/runner.py` - Runner管理核心
- `backend/bot/handlers.py` - Telegram处理逻辑
- `backend/config.py` - 配置管理
- `backend/main.py` - 应用启动

## 🔄 后续优化建议

1. **持久化Session状态**: 重启后恢复Session
2. **更细粒度的监控**: 添加Prometheus指标
3. **优先级队列**: 高优先级请求优先处理
4. **分布式部署**: 支持多实例负载均衡

---

**版本**: v1.1
**日期**: 2026-01-31
**重构负责人**: Claude Sonnet 4.5
