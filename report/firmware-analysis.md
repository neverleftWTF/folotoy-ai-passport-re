# 固件分析报告（脱敏版）

> 分析对象：一台 FoloToy AI Passport 设备的 8MB Flash 全量镜像
> 固件身份：项目名 `trae_card`，版本 v1.0.0，构建日期 2026-08，ESP-IDF v5.5.3，目标 ESP32-C3
> 所有设备身份信息（SN/ProductKey/用户名）均已脱敏

## 1. 硬件资源

| 资源 | 规格 | 证据 |
|---|---|---|
| MCU | ESP32-C3（RISC-V，无 PSRAM） | 镜像头 `Detected image type: ESP32-C3` |
| Flash | 8MB | 分区表覆盖 0x0–0x800000 |
| 屏幕 | ST7789 240×320，LVGL 9.x | 组件 `disp_st7789`、启动阶段 `10-display+lvgl` |
| 背光 | LEDC PWM 0–100% | `set_backlight %u%% (ready=%d duty=%u/%u)` |
| 按键 | 3 键 ADC 分压（UP/DOWN/OK） | 组件 `btn_adc` / `lvgl_btn` |
| 音频 | ES8311 codec，I2S 全双工（喇叭+麦克风），RTTTL 音效引擎 | 组件 `audio_es8311`；旋律 coin/die/ok/warn |
| 电池 | CW2017 电量计，EMA 平滑，缺失降级为虚拟电量 | 中文日志 |
| 无线 | BLE（NimBLE，BLE 5.0 扩展广播，SMP 加密） | 启动阶段 `20-ble-controller`/`30-ble-gatt+img` |
| 无 | **无 Wi-Fi 驱动/lwIP/HTTP/MQTT，无 NFC 代码** | 二进制扫描（`esp_wifi`/`lwip`/`nfc` 0 处） |
| USB | 原生 USB Serial/JTAG | AT 控制台载体 |
| 硬件版本 | C1.1 | `HardwareVersion` NVS 项 |

注：实物配有无源 NFC 标签（贴片），与主控无关，固件内无痕迹；机身标注的 NFC 读写即此标签，用于手机碰一碰配对。

## 2. 分区布局（零售布局）

| 分区 | 类型 | 偏移/大小 | 内容 |
|---|---|---|---|
| nvs | NVS | 0x9000, 24K | 配置、phy 校准、BLE 名称候选 |
| phy_init | data | 0xF000, 4K | RF 校准 |
| factory | app | 0x10000, 3M | 主固件（6 段镜像） |
| imgstore | spiffs | 0x310000, 128K | 图片缓存 |
| imgframe | spiffs | 0x330000, 152K | 帧缓存 |
| cardid | NVS | 0x356000, 16K | 云端三元组 + SN（出厂烧录，`AT+CARDID` 可写，sn 只读） |
| audio | spiffs | 0x37A000, 512K | 音乐文件 |
| imgava | spiffs | 0x3FA000, 1M | AVA1 头像包（8 帧 PNG + 偏移/CRC 索引） |

## 3. 启动流水线

```
00-boot → 10-display+lvgl → 20-ble-controller → 30-ble-gatt+img → 40-audio → 99-ready
```

伴随 60s 心跳（`hb-60s`）与堆监控（`[HEAP] free/min/max_blk/lv_peak`）。

## 4. 功能形态

| 模块 | 形态 |
|---|---|
| DASH 状态页 | 时钟 + 星期 + 电量；未对时显示 `--:--`；时间经 BLE 的 `time` 字段下发 |
| GAME | 俄罗斯方块（中文 UI、SCORE/BEST、NVS 持久化）+ LANE RUNNER 跑酷 |
| IMAGE | 图片浏览（BLE 传图至 imgstore/imgframe） |
| PET | 电子宠物：AVA1 头像动画、经验/等级/在线时长/睡眠、**代币经济（Token，上限 40000）** |
| 音乐 | RTTTL 开机/按键音 + audio 分区播放 |
| 系统 | 待机自动熄屏、功能键深睡唤醒（跳过引导与开机音）、背光/音量可调、新手引导 |

宠物状态 JSON 键集：`nickname, role, subtitle, avatar_name, battery, level, xp, xp_max, token, online, time, token_max, sleep_min, volume, game_clear, img_mode, fullscreen, avatar`

## 5. Token 经济（v3 广播协议）

- Token 为宠物代币余额，屏幕显示 `Token值 X / 40000`
- 官方链路：手机小程序 ↔ 网关 ↔ 设备 BLE 广播（v3 帧：type+txn+字段）
- 防伪：广播携带**签名**，接收方校验；固件日志含 `签名校验失败(可能有人在伪造,或网关密钥…)`
- 余额变动即落盘 NVS（`已保存到 NVS`）
- 本工具通过 BLE 直接写 `token` 字段同样落盘，但网关重新同步会覆盖

## 6. 与开源仓库的关系

FoloToy 开源仓库 `ai-passport`（`main` = 最小可运行 BSP 基线，`demo/*` = 各功能独立复刻：tetris-game / tamagezi / white-rabbit-pet / claude-buddy-port 等）与零售固件同芯片、同 IDF 5.5.3、同 BSP 组件命名。零售固件额外包含：AT 控制台、工厂自检、云端三元组、v3 广播经济、深睡、零售分区布局。

## 7. 时间子系统

- 无 SNTP/NTP（无网络栈），时间仅由 BLE `time` 字段下发，NVS 存 epoch
- **无时区处理**：epoch 按 UTC 直接显示 → 东八区用户需下发 `epoch + 8*3600`
- 深睡期间内部 RTC 续走；长期断电后回 `--:--` 等手机对时
