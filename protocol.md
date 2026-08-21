# 协议参考（实机逆向）

适用固件：`trae_card` v1.0.0（ESP-IDF v5.5.3 / ESP32-C3）

## 1. BLE

### 1.1 广播与连接

- 广播名 = 设备 SN（12 位十六进制小写）
- 连接后协商 MTU = 256（单次写上限约 253 字节）
- 设备待机（默认 300s，`standby_time` 可配）后深睡：USB 消失、BLE 停止广播，需按键唤醒
- 支持 SMP 加密配对（服务端含 mbedtls）

### 1.2 GATT 服务

服务 UUID：`54524145-4341-5244-0000-000000000000`（ASCII **"TRAECARD"**）

| 特征 UUID（末 4 位） | 属性 | 用途 |
|---|---|---|
| `...0010` | write / write-without-response | 命令通道 |
| `...0011` | notify | 响应 / 状态推送 |
| `...0012` | read | 设备信息：`ver(1B) count(1B) SN(16B) ProductKey(32B) hw(32B)` |
| `...0013` | read | 状态字（内容随状态变化） |
| `...0014` | notify | 截图通道 |

### 1.3 写入帧格式

```
[ver=0x01][type u8][len u16 LE][payload len 字节]
```

`type=0x01` → payload 为 **JSON 对象**，可含一个或多个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `time` | int | epoch 秒；固件**按 UTC 显示、无时区**，东八区需 `+8*3600` |
| `volume` | int 0–100 | 音量，落盘 NVS |
| `token` | int | 宠物代币余额（上限 `token_max`，默认 40000） |
| `token_max` | int | 代币上限 |
| `nickname` | str | 设备名（AT `+CONFIG` 中 `name=` 同源） |
| `xp` / `xp_max` / `level` | int | 宠物经验/等级 |
| `online` | int | 在线时长 |
| `sleep_min` | int | 睡眠分钟数 |
| `game_clear` | int | 游戏通关数 |
| `img_mode` / `fullscreen` | int | 图片模式/全屏 |
| `avatar` / `avatar_name` / `role` / `subtitle` | str/int | 头像与宠物设定 |
| `battery` | int | 电量 |

### 1.4 响应（`...0011` notify）

```
[ver u8][code u8]
```

| 响应 | 含义 |
|---|---|
| `01 01` | 成功 |
| `01 13` | JSON 解析失败 / 无生效字段 |
| `00 10` | 帧头非法（ver ≠ 0x01 等） |

## 2. USB Serial 控制台（原生 USB Serial/JTAG，115200 8N1）

### 2.1 AT 指令

| 指令 | 作用 | 实测响应 |
|---|---|---|
| `AT+CONFIG=?` / `at+config=?` | 读全量配置 | `+CONFIG: sn=…,key=…,hw=…,provisioned=…,volume=…,standby_time=…,guide_count=…,guide_remaining=…,name=…` |
| `AT+CONFIG=common,volume,0-100` | 设音量 | `+OK volume=80` |
| `AT+CONFIG=common,standby_time,秒` | 设待机时长 | `+OK` |
| `AT+CONFIG=common,guide_count,N` | 设引导次数 | `+OK` |
| `AT+CARDID?` | 读卡号/硬件/ProductKey 指纹 | `+CARDID: sn=…,hw=v1.0.0,pk_fp=…,provisioned=1` |
| `AT+CARDID=…` | 写入三元组（出厂用，sn 只读） | 参数：`sn/pk/hw`；错误码 `none/missing_param/too_long/sn_readonly/bad_char/unknown` |
| `AT+REBOOT` | 重启 | — |
| `AT+COMMAND=restart` | 重启 | — |
| `AT+TEST=INFO` 等 | 工厂自检 | `+TEST:INFO,ver=…,sn=…,heap=…,rst=…,PASS` |

错误统一前缀 `+ERR=`。未知配置项可用 `at+config=?` 查看。

### 2.2 工厂自检协议

`+TEST:` 系列：`I2C`（ES8311/CW2017）、`BTN`（10s 内按三键）、`INFO`、`AUDIO`、`BATT`、`BLE`、`ID`、`DISP`，汇总 `+TEST:RESULT,%s,fails=%d`。

## 3. 设备信息（`...0012` read）解析

```
01 01 <SN:16B ASCII> <ProductKey:32B ASCII> <hw:32B ASCII>
```

## 4. 已知限制 / 坑

- 授时：无时区处理，官方 App 重新对时后会再次偏差（+8h 显示错 8 小时）
- 深睡唤醒会跳过引导页和开机音乐
- 连接后 30ms 连接间隔，低延迟；notify 特征句柄见日志 `attr=18/25`
- 帧 payload ≤ 253B（MTU 256）
