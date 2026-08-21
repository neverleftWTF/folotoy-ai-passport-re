#!/usr/bin/env python3
"""
FoloToy AI Passport (trae_card v1.0.0) BLE 控制工具
==================================================
协议（实机逆向，详见 protocol.md）：
  BLE 服务  TRAECARD  54524145-4341-5244-0000-000000000000
    - ...0010  write / write-without-response  命令通道
    - ...0011  notify                          响应/事件推送
    - ...0012  read                            设备信息(SN/ProductKey/hw)
    - ...0013  read                            状态字
    - ...0014  notify                          截图通道
  广播名 = 设备 SN（12 位十六进制）
  帧格式   [ver=0x01][type u8][len u16 LE][payload]
    type=0x01 -> payload 为 JSON（time/volume/token/nickname/xp/...）
  响应(0x11 notify): [ver][code]  01 01=成功  01 13=JSON解析失败  00 10=帧头非法
  注意：设备待机后深睡需按键唤醒；MTU 协商后单帧≤253B

用法：
  python3 ble_tool.py info                 # 读设备信息（自动发现）
  python3 ble_tool.py settime              # 授时(东八区, 固件按UTC显示故+8h)
  python3 ble_tool.py set volume 80
  python3 ble_tool.py set token 500
  python3 ble_tool.py set nickname 小明
  python3 ble_tool.py set time 1787320467  # 原生 epoch 写入
  python3 ble_tool.py listen 15            # 订阅通知 15s
  python3 ble_tool.py --dev 4c11xxxxxxxx info   # 指定设备 SN
依赖: pip install bleak
"""
import asyncio
import json
import re
import struct
import sys
import time

from bleak import BleakScanner, BleakClient

SVC = "54524145-4341-5244-0000-000000000000"
CH_W = SVC[:-4] + "0010"
CH_N1 = SVC[:-4] + "0011"
CH_R1 = SVC[:-4] + "0012"
CH_R2 = SVC[:-4] + "0013"
CH_N2 = SVC[:-4] + "0014"

KNOWN_KEYS = ["time", "volume", "token", "token_max", "nickname", "xp",
              "xp_max", "level", "online", "sleep_min", "game_clear",
              "img_mode", "fullscreen", "avatar", "avatar_name",
              "role", "subtitle", "battery"]

TZ_OFFSET = 8 * 3600  # 东八区；固件无时区概念按 UTC 显示


def frame(typ: int, payload: bytes) -> bytes:
    return b"\x01" + bytes([typ]) + struct.pack("<H", len(payload)) + payload


async def find_device(name: str):
    devs = await BleakScanner.discover(timeout=8.0, return_adv=True)
    if name:
        for d, adv in devs.values():
            if (adv.local_name or "") == name:
                return d
    else:
        for d, adv in devs.values():
            n = adv.local_name or ""
            if re.fullmatch(r"[0-9a-f]{12}", n):
                return d
    return None


def fmt(b):
    if b is None:
        return "None"
    try:
        s = b.decode("utf-8")
        if all(32 <= ord(ch) < 127 or ch in "\r\n\t" for ch in s):
            return repr(s)
    except Exception:
        pass
    return b.hex()


async def main():
    args = sys.argv[1:]
    dev_name = None
    if args and args[0] == "--dev":
        dev_name = args[1]
        args = args[2:]
    cmd = args[0] if args else "info"

    d = await find_device(dev_name)
    if not d:
        print("设备未找到（深睡？按键唤醒后重试，或用 --dev 指定 SN）")
        return
    print(f"found {d.address} (adv name={dev_name or 'auto'})")
    async with BleakClient(d.address, timeout=15) as c:
        print("connected, mtu=", c.mtu_size if hasattr(c, "mtu_size") else "?")
        if cmd == "info":
            for uuid, label in [(CH_R1, "设备信息"), (CH_R2, "状态字")]:
                try:
                    v = await c.read_gatt_char(uuid)
                    print(f"{label} {uuid[-4:]}: {fmt(v)}")
                except Exception as e:
                    print(f"{label} 读取失败: {e}")
        elif cmd == "listen":
            async def on_n1(s, data):
                print(f"[0x11 notify] {data.hex()}")
            async def on_n2(s, data):
                print(f"[0x14 notify] {data.hex()}")
            await c.start_notify(CH_N1, on_n1)
            await c.start_notify(CH_N2, on_n2)
            secs = float(args[1]) if len(args) > 1 else 15
            print(f"listening {secs}s ...")
            await asyncio.sleep(secs)
            await c.stop_notify(CH_N1)
            await c.stop_notify(CH_N2)
        elif cmd == "settime":
            epoch_beijing = int(time.time()) + TZ_OFFSET
            payload = json.dumps({"time": epoch_beijing}).encode()
            await c.write_gatt_char(CH_W, frame(0x01, payload), response=True)
            print(f"授时(东八区)已发送: {payload.decode()}")
        elif cmd == "set" and len(args) >= 3:
            key, val = args[1], " ".join(args[2:])
            if key not in KNOWN_KEYS:
                print(f"未知字段 {key}，已知: {KNOWN_KEYS}")
                return
            if key in ("time", "volume", "token", "token_max", "xp",
                       "xp_max", "level", "online", "sleep_min",
                       "game_clear", "battery"):
                try:
                    val = int(val)
                except ValueError:
                    print(f"{key} 需要整数")
                    return

            async def on_n1(s, data):
                code = "成功" if data.hex() == "0101" else "见 protocol.md"
                print(f"[响应] {data.hex()} ({code})")
            await c.start_notify(CH_N1, on_n1)
            payload = json.dumps({key: val}).encode()
            await c.write_gatt_char(CH_W, frame(0x01, payload), response=True)
            print(f"已发送: {payload.decode()}")
            await asyncio.sleep(2)
            await c.stop_notify(CH_N1)
        else:
            print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
