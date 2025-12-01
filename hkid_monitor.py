#!/usr/bin/env python3
"""
香港身份证预约名额监控脚本
Hong Kong ID Card Appointment Quota Monitor

功能：
1. 定期检查入境处预约系统的名额状态
2. 当检测到比目标日期更早的可用名额时发送通知
3. 支持 Telegram 推送通知

使用方法：
1. 设置环境变量或在脚本中配置 Telegram Bot Token 和 Chat ID
2. 设置目标日期（你当前预约的日期）
3. 运行脚本：python3 hkid_monitor.py
"""

import requests
import json
import time
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 配置区域 ====================

# Telegram 配置（从环境变量读取或直接设置）
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID_HERE')

# 目标日期 - 你当前预约的日期（MM/DD/YYYY 格式）
# 脚本会监控所有比这个日期更早的可用名额
TARGET_DATE = os.environ.get('TARGET_DATE', '03/01/2026')

# 检查间隔（秒）- 建议不要太频繁以避免被封
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '300'))  # 默认5分钟

# 只监控特定办事处（留空则监控所有）
# 可选值: FTO, RHK, RKO, RTK, TMO, YLO
MONITOR_OFFICES = os.environ.get('MONITOR_OFFICES', '').split(',') if os.environ.get('MONITOR_OFFICES') else []

# API URL
API_URL = "https://eservices.es2.immd.gov.hk/surgecontrolgate/ticket/getSituation?svcId=579"

# 整点密集检查配置（中国时间）
# 在这些小时的整点前后会进行密集检查
HOT_HOURS = [0, 12]  # 0点和12点

# 整点密集检查的时间点（秒）：整点、30秒后、1分钟后
BURST_CHECK_OFFSETS = [0, 30, 60]

# 整点前多少秒开始准备（提前等待）
PREPARE_BEFORE_SECONDS = 5

# 中国时区
CHINA_TZ = pytz.timezone('Asia/Shanghai')

# ==================== 配置结束 ====================


# 办事处名称映射
OFFICE_NAMES = {
    'FTO': '火炭 (Fo Tan)',
    'RHK': '香港 (Hong Kong)',
    'RKO': '九龙 (Kowloon)',
    'RTK': '将军澳 (Tseung Kwan O)',
    'TMO': '屯门 (Tuen Mun)',
    'YLO': '元朗 (Yuen Long)'
}

# 名额状态映射
QUOTA_STATUS = {
    'quota-g': '🟢 有名额',
    'quota-y': '🟡 少量名额',
    'quota-r': '🔴 已满'
}


def parse_date(date_str: str) -> datetime:
    """解析日期字符串 (MM/DD/YYYY 格式)"""
    return datetime.strptime(date_str, '%m/%d/%Y')


def fetch_quota_data() -> Optional[Dict]:
    """获取预约名额数据"""
    try:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"获取数据失败: {e}")
        return None


def find_available_slots(data: Dict, target_date: datetime, offices: List[str] = None) -> List[Dict]:
    """
    查找可用的预约名额

    Args:
        data: API返回的数据
        target_date: 目标日期（查找比这个日期更早的名额）
        offices: 要监控的办事处列表（None表示全部）

    Returns:
        可用名额列表
    """
    available = []

    if 'data' not in data:
        return available

    for slot in data['data']:
        try:
            slot_date = parse_date(slot['date'])
            office_id = slot['officeId']
            quota_status = slot.get('quotaR', 'quota-r')

            # 过滤办事处
            if offices and office_id not in offices:
                continue

            # 检查是否比目标日期更早且有名额
            if slot_date < target_date and quota_status in ['quota-g', 'quota-y']:
                available.append({
                    'date': slot['date'],
                    'date_obj': slot_date,
                    'office_id': office_id,
                    'office_name': OFFICE_NAMES.get(office_id, office_id),
                    'status': quota_status,
                    'status_text': QUOTA_STATUS.get(quota_status, quota_status)
                })
        except (ValueError, KeyError) as e:
            logger.warning(f"解析数据错误: {e}")
            continue

    # 按日期排序
    available.sort(key=lambda x: x['date_obj'])
    return available


def send_telegram_notification(message: str) -> bool:
    """发送 Telegram 通知"""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE' or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID_HERE':
        logger.warning("Telegram 未配置，跳过推送通知")
        print(f"\n📱 通知内容:\n{message}\n")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram 通知发送成功")
        return True
    except requests.RequestException as e:
        logger.error(f"发送 Telegram 通知失败: {e}")
        return False


def test_telegram() -> bool:
    """测试 Telegram 连接"""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE' or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID_HERE':
        logger.warning("⚠️ Telegram 未配置，请设置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        return False

    logger.info("🔔 测试 Telegram 连接...")
    now = get_china_time().strftime('%Y-%m-%d %H:%M:%S')
    test_message = f"✅ <b>香港身份证预约监控已启动</b>\n\n"
    test_message += f"⏰ 启动时间（中国时间）: {now}\n"
    test_message += f"📅 目标日期: {TARGET_DATE}\n"
    test_message += f"🔥 整点检查时间: {HOT_HOURS} 点\n"
    test_message += f"⏱️ 常规检查间隔: {CHECK_INTERVAL} 秒\n\n"
    test_message += "监控已开始运行，发现新名额时会自动通知您。"

    success = send_telegram_notification(test_message)
    if success:
        logger.info("✅ Telegram 测试成功！")
    else:
        logger.error("❌ Telegram 测试失败，请检查配置")
    return success


def format_notification(slots: List[Dict], target_date: str) -> str:
    """格式化通知消息"""
    message = "🎉 <b>香港身份证预约名额提醒</b>\n\n"
    message += f"发现比您的预约日期 ({target_date}) 更早的可用名额：\n\n"

    for slot in slots[:10]:  # 最多显示10个
        message += f"📅 <b>{slot['date']}</b>\n"
        message += f"   📍 {slot['office_name']}\n"
        message += f"   {slot['status_text']}\n\n"

    if len(slots) > 10:
        message += f"... 还有 {len(slots) - 10} 个可用时段\n\n"

    message += "🔗 立即预约: https://www.gov.hk/tc/residents/immigration/idcard/hkic/bookregidcard.htm"

    return message


def get_earliest_available(data: Dict) -> Optional[Dict]:
    """获取最早的可用名额（不限日期）"""
    if 'data' not in data:
        return None

    for slot in data['data']:
        if slot.get('quotaR') in ['quota-g', 'quota-y']:
            return {
                'date': slot['date'],
                'office_id': slot['officeId'],
                'office_name': OFFICE_NAMES.get(slot['officeId'], slot['officeId']),
                'status': slot['quotaR'],
                'status_text': QUOTA_STATUS.get(slot['quotaR'], slot['quotaR'])
            }
    return None


def get_china_time() -> datetime:
    """获取当前中国时间"""
    return datetime.now(CHINA_TZ)


def get_seconds_to_next_hot_hour() -> tuple:
    """
    计算距离下一个整点检查时间的秒数

    Returns:
        (seconds_to_hot_hour, next_hot_hour): 距离下个整点的秒数和那个整点的小时数
    """
    now = get_china_time()
    current_hour = now.hour
    current_minute = now.minute
    current_second = now.second

    # 当前时间距离本小时整点的秒数
    seconds_into_hour = current_minute * 60 + current_second

    # 找到下一个热门小时
    next_hot_hour = None
    for hot_hour in sorted(HOT_HOURS):
        if hot_hour > current_hour:
            next_hot_hour = hot_hour
            break

    if next_hot_hour is None:
        # 没找到今天的，用明天的第一个
        next_hot_hour = sorted(HOT_HOURS)[0]
        hours_until = (24 - current_hour) + next_hot_hour
    else:
        hours_until = next_hot_hour - current_hour

    # 如果正好是热门小时且还在第一分钟内，返回0
    if current_hour in HOT_HOURS and seconds_into_hour <= max(BURST_CHECK_OFFSETS) + 10:
        return (0, current_hour)

    # 计算秒数
    seconds_to_hot = (hours_until * 3600) - seconds_into_hour

    return (seconds_to_hot, next_hot_hour)


def is_burst_check_time() -> bool:
    """检查当前是否是密集检查时间（整点前后）"""
    now = get_china_time()

    if now.hour not in HOT_HOURS:
        return False

    # 在整点后的检查窗口内
    seconds_into_hour = now.minute * 60 + now.second
    return seconds_into_hour <= max(BURST_CHECK_OFFSETS) + 10


def perform_burst_checks(target_date: datetime, last_notified: set, offices_to_check: List[str]) -> set:
    """
    在整点时执行密集检查（整点、30秒后、1分钟后）

    Returns:
        更新后的 last_notified 集合
    """
    now = get_china_time()
    logger.info(f"🔥 整点密集检查模式启动！当前中国时间: {now.strftime('%H:%M:%S')}")

    for i, offset in enumerate(BURST_CHECK_OFFSETS):
        # 计算需要等待的时间
        current_second = get_china_time().minute * 60 + get_china_time().second
        wait_time = offset - current_second

        if wait_time > 0:
            logger.info(f"⏳ 等待 {wait_time} 秒后进行第 {i+1} 次检查...")
            time.sleep(wait_time)

        # 执行检查
        check_time = get_china_time().strftime('%H:%M:%S')
        logger.info(f"🔍 第 {i+1}/{len(BURST_CHECK_OFFSETS)} 次密集检查 [{check_time}]")

        data = fetch_quota_data()
        if data:
            print_status_summary(data)
            available = find_available_slots(data, target_date, offices_to_check)

            if available:
                slot_keys = {f"{s['date']}_{s['office_id']}" for s in available}
                new_slots = slot_keys - last_notified

                if new_slots:
                    new_available = [s for s in available if f"{s['date']}_{s['office_id']}" in new_slots]
                    logger.info(f"🎉🎉🎉 发现 {len(new_available)} 个新名额！")

                    message = f"⚡ <b>整点放号提醒</b> [{check_time}]\n\n"
                    message += format_notification(new_available, TARGET_DATE)
                    send_telegram_notification(message)

                    last_notified.update(new_slots)
                else:
                    logger.info(f"检查完成，暂无新名额")
            else:
                logger.info("本次检查无可用名额")
        else:
            logger.warning("获取数据失败")

        # 短暂等待避免请求过快（除了最后一次）
        if i < len(BURST_CHECK_OFFSETS) - 1:
            time.sleep(0.5)

    logger.info("✅ 整点密集检查完成")
    return last_notified


def print_status_summary(data: Dict):
    """打印当前状态摘要"""
    if 'data' not in data:
        return

    # 统计各办事处最早可用日期
    earliest_by_office = {}
    for slot in data['data']:
        office = slot['officeId']
        status = slot.get('quotaR', 'quota-r')

        if status in ['quota-g', 'quota-y'] and office not in earliest_by_office:
            earliest_by_office[office] = {
                'date': slot['date'],
                'status': QUOTA_STATUS.get(status, status)
            }

    print("\n" + "="*60)
    print("📊 当前各办事处最早可预约日期:")
    print("="*60)

    for office_id, info in sorted(earliest_by_office.items()):
        office_name = OFFICE_NAMES.get(office_id, office_id)
        print(f"  {office_name}: {info['date']} {info['status']}")

    if not earliest_by_office:
        print("  暂无可用名额")

    print("="*60 + "\n")


def run_monitor():
    """运行监控"""
    logger.info("=" * 50)
    logger.info("香港身份证预约名额监控启动")
    logger.info("=" * 50)
    logger.info(f"目标日期: {TARGET_DATE}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"监控办事处: {MONITOR_OFFICES if MONITOR_OFFICES else '全部'}")
    logger.info(f"整点密集检查时间（中国时间）: {HOT_HOURS} 点")
    logger.info(f"当前中国时间: {get_china_time().strftime('%Y-%m-%d %H:%M:%S')}")

    # 启动时测试 Telegram
    test_telegram()

    target_date = parse_date(TARGET_DATE)
    last_notified = set()  # 避免重复通知
    offices_to_check = MONITOR_OFFICES if MONITOR_OFFICES else None

    while True:
        try:
            # 检查是否接近整点检查时间
            seconds_to_hot, next_hot = get_seconds_to_next_hot_hour()

            # 如果距离整点不到准备时间，进入等待状态
            if 0 < seconds_to_hot <= PREPARE_BEFORE_SECONDS + CHECK_INTERVAL:
                wait_time = max(0, seconds_to_hot - PREPARE_BEFORE_SECONDS)
                logger.info(f"⏰ 距离 {next_hot}:00 整点检查还有 {seconds_to_hot} 秒")
                if wait_time > 0:
                    logger.info(f"⏳ 等待 {wait_time} 秒后开始整点密集检查...")
                    time.sleep(wait_time)

                # 执行整点密集检查
                last_notified = perform_burst_checks(target_date, last_notified, offices_to_check)

                # 整点检查后等待一段时间再恢复正常检查
                logger.info(f"整点检查完成，{CHECK_INTERVAL} 秒后恢复正常检查")
                time.sleep(CHECK_INTERVAL)
                continue

            # 正常检查
            now_china = get_china_time().strftime('%H:%M:%S')
            logger.info(f"正在检查预约名额... [中国时间 {now_china}]")
            data = fetch_quota_data()

            if data:
                # 打印状态摘要
                print_status_summary(data)

                # 查找可用名额
                available = find_available_slots(data, target_date, offices_to_check)

                if available:
                    # 生成唯一标识，避免重复通知
                    slot_keys = {f"{s['date']}_{s['office_id']}" for s in available}
                    new_slots = slot_keys - last_notified

                    if new_slots:
                        new_available = [s for s in available if f"{s['date']}_{s['office_id']}" in new_slots]

                        logger.info(f"🎉 发现 {len(new_available)} 个新的可用名额！")

                        # 发送通知
                        message = format_notification(new_available, TARGET_DATE)
                        send_telegram_notification(message)

                        # 更新已通知列表
                        last_notified.update(new_slots)
                    else:
                        logger.info(f"有 {len(available)} 个可用名额（已通知过）")
                else:
                    logger.info("暂无比目标日期更早的可用名额")
                    # 显示最早可用的名额
                    earliest = get_earliest_available(data)
                    if earliest:
                        logger.info(f"当前最早可用: {earliest['date']} @ {earliest['office_name']} {earliest['status_text']}")
            else:
                logger.warning("获取数据失败，将在下次检查时重试")

            # 计算下次检查时间，显示距离整点的时间
            seconds_to_hot, next_hot = get_seconds_to_next_hot_hour()
            hours = seconds_to_hot // 3600
            mins = (seconds_to_hot % 3600) // 60
            logger.info(f"下次检查: {CHECK_INTERVAL} 秒后 | 距离 {next_hot}:00 整点检查: {hours}小时{mins}分钟")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("监控已停止")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)  # 出错后等待1分钟再重试


def check_once():
    """单次检查（用于测试）"""
    logger.info("执行单次检查...")
    data = fetch_quota_data()

    if data:
        print_status_summary(data)

        target_date = parse_date(TARGET_DATE)
        offices_to_check = MONITOR_OFFICES if MONITOR_OFFICES else None
        available = find_available_slots(data, target_date, offices_to_check)

        if available:
            print(f"\n✅ 发现 {len(available)} 个比 {TARGET_DATE} 更早的可用名额:\n")
            for slot in available:
                print(f"  📅 {slot['date']} @ {slot['office_name']} {slot['status_text']}")
        else:
            print(f"\n❌ 暂无比 {TARGET_DATE} 更早的可用名额")
            earliest = get_earliest_available(data)
            if earliest:
                print(f"\n当前最早可用: {earliest['date']} @ {earliest['office_name']} {earliest['status_text']}")
    else:
        print("获取数据失败")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 单次检查模式
        check_once()
    else:
        # 持续监控模式
        run_monitor()
