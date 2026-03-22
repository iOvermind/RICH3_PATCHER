import os
import re
from PIL import Image

def get_grouped_planar(blocks):
    c = len(blocks)
    res = bytearray(c * 4)
    for i in range(c):
        res[i]         = blocks[i][0]
        res[c + i]     = blocks[i][1]
        res[2*c + i]   = blocks[i][2]
        res[3*c + i]   = blocks[i][3]
    return res

def is_solid_block(b):
    return b[0] in (0, 255) and b[1] in (0, 255) and b[2] in (0, 255) and b[3] in (0, 255)

def get_solid_color_index(b):
    return (1 if b[0] else 0) | (2 if b[1] else 0) | (4 if b[2] else 0) | (8 if b[3] else 0)

def compress_smkf(bmp_path):
    img = Image.open(bmp_path)
    if img.mode != 'P':
        raise ValueError(f"幹，{bmp_path} 必須是索引色 (P) 模式！")
        
    width, height = img.size
    if width != 640 or height != 400:
        raise ValueError(f"尺寸不對！圖檔必須是 640x400。")

    pixels = img.load()
    blocks = []
    
    for block_idx in range(width * height // 8):
        y = block_idx // (width // 8)
        base_x = (block_idx % (width // 8)) * 8
        p0 = p1 = p2 = p3 = 0
        for i in range(8):
            c = pixels[base_x + i, y]
            bit = 7 - i
            p0 |= ((c & 1) >> 0) << bit
            p1 |= ((c & 2) >> 1) << bit
            p2 |= ((c & 4) >> 2) << bit
            p3 |= ((c & 8) >> 3) << bit
        blocks.append(bytes([p0, p1, p2, p3]))

    encoded = bytearray()
    pos = 0
    total = len(blocks)
    positions = {}
    raw_buffer = []

    def flush_raw():
        nonlocal raw_buffer, encoded
        if not raw_buffer: return
        idx = 0
        while idx < len(raw_buffer):
            # 避開 0x06 (16-bit)，強制切成最大 255 的塊
            chunk = raw_buffer[idx : idx+255]
            c = len(chunk)
            if c == 1:
                encoded.append(0x04)
                encoded.extend(chunk[0])
            else:
                encoded.extend([0x05, c])
                encoded.extend(get_grouped_planar(chunk))
            idx += c
        raw_buffer = []

    while pos < total:
        # 計算連續純色長度 (包含原本的黑色)
        len_solid = 0
        solid_c = 0
        if is_solid_block(blocks[pos]):
            b = blocks[pos]
            solid_c = get_solid_color_index(b)
            while pos + len_solid < total and blocks[pos + len_solid] == b:
                len_solid += 1

        # 字典匹配 (嚴格禁止重疊 Overlapping)
        len_dict = 0
        offset_dict = 0
        candidates = positions.get(blocks[pos], [])
        
        for start_pos in reversed(candidates):
            offset = pos - start_pos
            if offset > 65535:
                continue
                
            # 【關鍵】長度不能大於 offset，避免 DOS memcpy 抓到垃圾記憶體
            max_l = min(total - pos, offset)
            if max_l > 65535: max_l = 65535
            
            l = 0
            while l < max_l and blocks[start_pos + l] == blocks[pos + l]:
                l += 1
            
            if l > len_dict:
                len_dict = l
                offset_dict = offset
                if len_dict >= 255: 
                    break 

        # 決策邏輯
        if len_solid >= 2 and len_solid >= len_dict:
            flush_raw()
            if len_solid <= 255:
                encoded.extend([0x07, solid_c, len_solid])
            else:
                encoded.extend([0x08, solid_c, len_solid & 0xFF, (len_solid >> 8) & 0xFF])
                
            for i in range(len_solid):
                positions.setdefault(blocks[pos+i], []).append(pos+i)
            pos += len_solid
            
        elif len_dict >= 2:
            flush_raw()
            c = len_dict
            d = offset_dict
            if d <= 255 and c <= 255:
                encoded.extend([0x0F, d, c])
            elif d <= 255 and c > 255:
                encoded.extend([0x10, d, c & 0xFF, (c >> 8) & 0xFF])
            elif d > 255 and c <= 255:
                encoded.extend([0x11, d & 0xFF, (d >> 8) & 0xFF, c])
            else:
                encoded.extend([0x12, d & 0xFF, (d >> 8) & 0xFF, c & 0xFF, (c >> 8) & 0xFF])
                
            for i in range(len_dict):
                positions.setdefault(blocks[pos+i], []).append(pos+i)
            pos += len_dict
            
        else:
            raw_buffer.append(blocks[pos])
            positions.setdefault(blocks[pos], []).append(pos)
            pos += 1
            
    flush_raw()
    encoded.append(0x00)
    return encoded

def rebuild_mkf(orig_mkf_path, target_bmp_path, out_mkf_path):
    match = re.search(r'\d+', target_bmp_path)
    if not match:
        print("檔名沒數字啦，請用 screen_19.bmp 這種格式。")
        return
    
    target_idx = int(match.group()) - 1 

    with open(orig_mkf_path, 'rb') as f:
        data = f.read()

    mkf_len = len(data)
    offsets = []
    curr = 0
    while curr < mkf_len:
        offset = int.from_bytes(data[curr:curr+4], byteorder='little')
        offsets.append(offset)
        curr += 4
        if len(offsets) > 1 and curr >= offsets[0]:
            break

    chunks = []
    for i in range(len(offsets) - 1):
        chunks.append(data[offsets[i]:offsets[i+1]])

    if target_idx >= len(chunks):
        print(f"靠，你指定的編號超過了，MKF 裡面只有 {len(chunks)} 張圖！")
        return

    print(f"正在壓制 {target_bmp_path} (禁止重疊安全版)...")
    new_smkf = compress_smkf(target_bmp_path)
    print(f"壓縮完畢！原大小: {len(chunks[target_idx])} bytes, 新大小: {len(new_smkf)} bytes")

    chunks[target_idx] = new_smkf

    N = len(chunks)
    current_offset = (N + 1) * 4
    new_offsets = []
    for chunk in chunks:
        new_offsets.append(current_offset)
        current_offset += len(chunk)
    new_offsets.append(current_offset)

    print(f"正在重組 {out_mkf_path}...")
    with open(out_mkf_path, 'wb') as f:
        for off in new_offsets:
            f.write(off.to_bytes(4, byteorder='little'))
        for chunk in chunks:
            f.write(chunk)
            
    print("重組完成！去開遊戲看看這次還會不會破圖！")

if __name__ == "__main__":
    rebuild_mkf("SCREEN.MKF", "screen_19.bmp", "SCREEN_NEW.MKF")