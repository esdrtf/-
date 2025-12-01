# Telegram 通知设置指南

## 1. 创建 Telegram Bot

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令
3. 按提示输入机器人名称和用户名
4. 保存返回的 **Bot Token**（类似：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

## 2. 获取你的 Chat ID

方法一：使用 @userinfobot
1. 在 Telegram 搜索 `@userinfobot`
2. 发送任意消息
3. 它会返回你的 Chat ID（一串数字）

方法二：使用 @getidsbot
1. 搜索 `@getidsbot`
2. 发送 `/start`
3. 获取你的 User ID

## 3. 配置监控脚本

### 方式一：环境变量（推荐）

```bash
export TELEGRAM_BOT_TOKEN="你的Bot Token"
export TELEGRAM_CHAT_ID="你的Chat ID"
export TARGET_DATE="你当前预约的日期"  # 格式: MM/DD/YYYY
export CHECK_INTERVAL="300"  # 检查间隔（秒）

python3 hkid_monitor.py
```

### 方式二：直接编辑脚本

编辑 `hkid_monitor.py` 文件中的配置区域：

```python
TELEGRAM_BOT_TOKEN = '你的Bot Token'
TELEGRAM_CHAT_ID = '你的Chat ID'
TARGET_DATE = '03/01/2026'  # 修改为你的预约日期
CHECK_INTERVAL = 300  # 检查间隔（秒）
```

## 4. 运行脚本

```bash
# 单次检查（测试用）
python3 hkid_monitor.py --once

# 持续监控
python3 hkid_monitor.py

# 后台运行
nohup python3 hkid_monitor.py > monitor.log 2>&1 &
```

## 5. 可选配置

### 只监控特定办事处

```bash
export MONITOR_OFFICES="RHK,RKO"  # 只监控香港和九龙
```

办事处代码：
- `FTO` - 火炭
- `RHK` - 香港
- `RKO` - 九龙
- `RTK` - 将军澳
- `TMO` - 屯门
- `YLO` - 元朗

## 测试 Telegram 通知

发送测试消息：
```bash
curl -X POST "https://api.telegram.org/bot你的TOKEN/sendMessage" \
  -d "chat_id=你的CHAT_ID" \
  -d "text=测试消息"
```
