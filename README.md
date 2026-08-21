# FoloToy AI Passport 逆向研究工具集

对 FoloToy AI Passport（固件项目名 `trae_card`）可穿戴设备的**互通性研究**成果：BLE 协议文档、AT 控制台指令表、固件功能分析，以及一个开箱即用的 Python 控制工具。

> ⚠️ 免责声明
> - 本项目**仅为学习与设备互通性研究**目的，非官方工具，未获得 FoloToy 官方授权。
> - 仓库内**不包含任何固件二进制、镜像切片、反汇编产物或云端凭证**。
> - 使用本工具修改设备数据（Token、昵称等）可能违反设备/小程序服务条款，请自行评估风险。
> - 设备名称、序列号、ProductKey 等身份信息已在文档中脱敏。

## 目录

| 文件 | 内容 |
|---|---|
| [protocol.md](protocol.md) | BLE GATT 协议 + USB AT 指令完整参考 |
| [report/firmware-analysis.md](report/firmware-analysis.md) | 固件功能/硬件/分区脱敏分析报告 |
| [tools/ble_tool.py](tools/ble_tool.py) | BLE 控制工具：授时/改音量/改 Token/改名/读信息 |
| [tools/nvs_parse.py](tools/nvs_parse.py) | 通用 ESP32 NVS 分区解析器 |

## 快速开始

```bash
pip install bleak
python3 tools/ble_tool.py info            # 读设备信息（自动发现广播名为 12 位十六进制 SN 的设备）
python3 tools/ble_tool.py settime         # 授时（东八区）
python3 tools/ble_tool.py set volume 80
python3 tools/ble_tool.py set token 500
python3 tools/ble_tool.py set nickname 小名
python3 tools/ble_tool.py listen 15
```

指定设备（当环境中有多台时）：

```bash
python3 tools/ble_tool.py --dev 4c11xxxxxxxx info
```

## 关键结论速览

- 设备 = ESP32-C3 + 240×320 彩屏 + 3 键 + ES8311 音频 + CW2017 电池 + **仅 BLE 联网**（无 Wi-Fi/NFC 芯片）
- BLE 服务 UUID `54524145-4341-5244-0000-000000000000`（ASCII "TRAECARD"）
- 写协议：`[0x01][type][len u16LE][payload]`，`type=0x01` 时 payload 为 JSON
- 支持的 JSON 字段：`time / volume / token / nickname / xp / level / ...`（详见 protocol.md）
- USB 串口 AT 控制台：`AT+CONFIG=?`、`AT+CONFIG=common,volume,0-100`、`AT+CARDID?`、`AT+TEST=...`
- 设备深睡（默认待机 300s）后需按键唤醒，USB 串口会消失
- 固件无时区概念（按 UTC 显示 epoch），授时需 +8h 补偿

## License

MIT
