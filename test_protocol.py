"""测试消息协议"""
import sys
sys.path.insert(0, 'd:/desktop/Stonk')

from shared.message_protocol import MessageType, parse_message

# 测试所有新消息类型
test_types = [
    "ADMIN_LIST_STOCKS",
    "ADMIN_CREATE_ROBOT",
    "ADMIN_LIST_ROBOTS",
    "ROBOT_LIST",
    "ROOM_ROBOT_LIST",
]

for t in test_types:
    try:
        mt = MessageType[t]
        print(f"OK: {t} = {mt.value}")
    except KeyError as e:
        print(f"ERROR: {t} not found: {e}")

# 测试 parse_message
try:
    import json
    msg = json.dumps({"type": "ADMIN_LIST_STOCKS", "data": {}, "timestamp": 123})
    result = parse_message(msg)
    print(f"parse_message OK: {result['type']}")
except Exception as e:
    print(f"parse_message ERROR: {e}")
