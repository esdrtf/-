#!/bin/bash
# 香港身份证预约监控启动脚本

# ==================== 配置区域 ====================
# 请修改以下配置

# Telegram 配置
export TELEGRAM_BOT_TOKEN="8283010813:AAF9rhH3yV_oD5EUTleCiWNvQs3HPQ6M41U"
export TELEGRAM_CHAT_ID="6190291125"

# 你当前预约的日期（格式：MM/DD/YYYY）
# 脚本会监控所有比这个日期更早的可用名额
export TARGET_DATE="22/12/2025"

# 检查间隔（秒）- 建议 300-600 秒
export CHECK_INTERVAL="300"

# 只监控特定办事处（留空监控全部）
# 可选: FTO(火炭), RHK(香港), RKO(九龙), RTK(将军澳), TMO(屯门), YLO(元朗)
export MONITOR_OFFICES=""

# ==================== 配置结束 ====================

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查 Python 和依赖
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# 安装依赖
pip3 install -q -r requirements.txt 2>/dev/null

echo "================================"
echo "香港身份证预约监控"
echo "================================"
echo "目标日期: $TARGET_DATE"
echo "检查间隔: $CHECK_INTERVAL 秒"
echo "监控办事处: ${MONITOR_OFFICES:-全部}"
echo "================================"
echo ""

# 运行监控
python3 hkid_monitor.py
