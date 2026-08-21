#!/usr/bin/env python3
"""Minimal NVS partition parser for ESP32 (NVS v2, 4KB pages, no encryption)."""
import struct
import sys

def parse_nvs(path):
    d = open(path, 'rb').read()
    n_pages = len(d) // 4096
    entries = []
    for p in range(n_pages):
        page = d[p*4096:(p+1)*4096]
        if page[:4] not in (b'\xff\xff\xff\xff', b'\xfe\xff\xff\xff'):
            state = page[0]
            seq = struct.unpack('<I', page[4:8])[0]
            used = struct.unpack('<H', page[32:34])[0]
            entries.append(('PAGE', p, state, seq, used))
        i = 0
        while i < 4096 - 32:
            st = page[i]
            if st == 0xFF:
                break
            if st in (0xFE, 0xFC):
                i += 32
                continue
            ns_idx, typ, span = page[i+1], page[i+2], page[i+3]
            if span == 0:
                span = 1
            key = page[i+4:i+12].split(b'\x00')[0].decode('latin1', 'replace')
            # chunk index & crc
            # value offsets: for single-span entries value starts at i+32
            raw = page[i+32:i+32*span]
            val = None
            if typ == 0x01 and len(raw) >= 1:
                val = raw[0]
            elif typ == 0x11 and len(raw) >= 1:
                val = struct.unpack('b', raw[:1])[0]
            elif typ == 0x02 and len(raw) >= 2:
                val = struct.unpack('<H', raw[:2])[0]
            elif typ == 0x12 and len(raw) >= 2:
                val = struct.unpack('<h', raw[:2])[0]
            elif typ == 0x04 and len(raw) >= 4:
                val = struct.unpack('<I', raw[:4])[0]
            elif typ == 0x14 and len(raw) >= 4:
                val = struct.unpack('<i', raw[:4])[0]
            elif typ == 0x08 and len(raw) >= 8:
                val = struct.unpack('<Q', raw[:8])[0]
            elif typ == 0x21 and len(raw) >= 1:
                ln = raw[0]
                val = raw[1:1+ln].decode('utf-8', 'replace')
            elif typ == 0x41 and len(raw) >= 2:
                ln = struct.unpack('<H', raw[:2])[0]
                val = raw[2:2+ln]
            elif typ in (0x48, 0x42):
                val = f'<{typ:02x} blob>'
            else:
                val = f'<typ {typ:02x}, {span} span>'
            entries.append((p, ns_idx, hex(typ), key, val))
            i += 32 * span
    return entries

for path in sys.argv[1:]:
    print(f'===== {path} =====')
    for e in parse_nvs(path):
        print(' ', e)
