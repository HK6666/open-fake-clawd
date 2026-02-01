# ccBot 快速参考

## 🚀 新功能速览

### 智能消息处理
```python
# 自动批量更新，减少 API 调用
# 智能代码块保持
# 优雅的长消息分片
```

### 新增命令

#### `/tree [depth]` - 目录树
```
用法: /tree 3
显示最多 3 层深的目录结构
```

#### `/stats` - 统计信息
```
显示:
• 总会话数
• 总消息数
• 总成本
• 平均值
• 最常用目录
```

#### `/clear` - 清空历史
```
清除当前会话的消息历史
但保持会话活跃
自动保存到文件
```

---

## 📋 完整命令列表

### 会话管理
| 命令 | 说明 |
|------|------|
| `/new` | 开始新会话 |
| `/continue` | 继续上次会话 |
| `/sessions` | 列出所有会话 |
| `/clear` | 清空会话历史 |
| `/end` | 结束当前会话 |
| `/export` | 导出会话记录 |

### 文件系统
| 命令 | 说明 |
|------|------|
| `/ls` | 列出目录内容 |
| `/tree [depth]` | 显示目录树 |
| `/cd <path>` | 切换目录 |
| `/pwd` | 显示当前路径 |

### 状态和控制
| 命令 | 说明 |
|------|------|
| `/status` | 显示当前状态 |
| `/stats` | 使用统计 |
| `/stop` | 停止当前任务 |

### 辅助功能
| 命令 | 说明 |
|------|------|
| `/menu` | 快捷菜单 |
| `/actions` | 快速操作 |
| `/help` | 帮助信息 |

---

## ⚡ 快速操作按钮

点击 `/actions` 后可选择：

- 🔍 **Review Code** - 代码审查
- 🐛 **Debug** - 调试帮助
- 📝 **Explain** - 解释代码
- ✨ **Improve** - 改进建议
- 🧪 **Write Tests** - 编写测试
- 📖 **Add Docs** - 添加文档

---

## 🎯 最佳实践

### 1. 会话管理
```
✅ 定期使用 /clear 清理历史（节省成本）
✅ 使用 /export 保存重要对话
✅ 使用 /end 正式结束会话（更新 USER.md）
```

### 2. 目录导航
```
✅ 使用 /cd 切换到项目目录
✅ 使用 /tree 快速查看结构
✅ 使用 /ls 查看文件列表
```

### 3. 成本控制
```
✅ 定期检查 /stats
✅ 清理不需要的历史消息
✅ 使用简洁的提示词
```

---

## 🔧 配置选项

### 环境变量
```env
# 核心配置
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_USERS=123456,789012

# 性能调优
MAX_CONCURRENT_SESSIONS=5
SESSION_TIMEOUT_MINUTES=120
MAX_MESSAGE_HISTORY=100

# 功能开关
AUTO_SAVE_SESSIONS=true
```

---

## ⚠️ 故障排除

### 消息未响应
```
1. 检查 /status 查看状态
2. 使用 /stop 停止卡住的任务
3. 使用 /new 开始新会话
```

### 速率限制
```
默认: 10 请求/分钟
超限时会显示等待时间
```

### 权限错误
```
确保 APPROVED_DIRECTORY 设置正确
使用 /pwd 检查当前目录
```

---

## 📊 消息格式

### 成功消息
```
✅ Task completed
💬 Messages: 15
💰 Total cost: $0.25
```

### 错误消息
```
❌ Error: {type}

Details: {description}

建议:
• 尝试的操作
• 检查的配置
```

### 进度消息
```
🤔 Processing your request...
🤖 Invoking Claude Code CLI...
🔧 Using tool: Read
```

---

## 🎨 使用技巧

### Tip 1: 使用菜单按钮
```
发送 /menu 获取交互式按钮
比打字命令更快更方便
```

### Tip 2: 查看目录树
```
/tree 2  # 查看 2 层结构
快速了解项目布局
```

### Tip 3: 监控成本
```
/stats  # 定期检查
了解使用情况和成本
```

### Tip 4: 保存重要对话
```
/export  # 在结束前导出
保留有价值的对话记录
```

### Tip 5: 快速操作
```
使用 /actions 快捷按钮
常见任务一键启动
```

---

## 📱 示例工作流

### 开始新项目
```
1. /cd ~/projects/my-app
2. /tree 3
3. "请帮我审查这个项目的代码结构"
4. /stats  # 查看成本
5. /export  # 保存建议
```

### 调试问题
```
1. /actions → 🐛 Debug
2. 描述问题
3. 按建议修改
4. /clear  # 清理历史
```

### 代码审查
```
1. /cd ~/my-repo
2. /actions → 🔍 Review Code
3. 查看建议
4. /export  # 保存报告
5. /end  # 结束并更新记忆
```

---

## 🔗 相关资源

- **完整文档**: `README.md`
- **优化总结**: `OPTIMIZATION_SUMMARY.md`
- **配置示例**: `.env.example`

---

**版本**: 1.0
**更新**: 2026-01-31
**状态**: ✅ 生产就绪
