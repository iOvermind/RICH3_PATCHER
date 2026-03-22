import os
import re
import glob
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
        len_solid = 0
        solid_c = 0
        if is_solid_block(blocks[pos]):
            b = blocks[pos]
            solid_c = get_solid_color_index(b)
            while pos + len_solid < total and blocks[pos + len_solid] == b:
                len_solid += 1

        len_dict = 0
        offset_dict = 0
        candidates = positions.get(blocks[pos], [])
        
        for start_pos in reversed(candidates):
            offset = pos - start_pos
            if offset > 65535:
                continue
                
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


# =====================================================================
# 新增功能區
# =====================================================================

def export_to_bin(bmp_path, out_bin_path):
    """目標 1：將單一 BMP 壓縮成 .bin 格式，用來上傳 GitHub"""
    print(f"[{bmp_path}] 正在壓制為 SMKF 二進位檔...")
    encoded = compress_smkf(bmp_path)
    with open(out_bin_path, 'wb') as f:
        f.write(encoded)
    print(f"爽啦！ {out_bin_path} 產生完畢，大小: {len(encoded)} bytes。直接把這個推上 repo 就對了！")


def batch_patch_mkf(orig_mkf_path, patch_dir, out_mkf_path):
    """目標 2：自動掃描資料夾，把所有 .bmp 或 .bin 批次塞回 MKF"""
    if not os.path.exists(orig_mkf_path):
        print(f"靠背，找不到原始檔 {orig_mkf_path}！")
        return

    with open(orig_mkf_path, 'rb') as f:
        data = f.read()

    # 解析原始 MKF
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

    if not os.path.exists(patch_dir):
        os.makedirs(patch_dir)
        print(f"幫你建了 {patch_dir} 資料夾，把補丁丟進去再跑一次吧！")
        return

    # 找尋所有 screen_XX.bmp 和 screen_XX.bin
    patch_files = glob.glob(os.path.join(patch_dir, "screen_*.*"))
    patch_count = 0

    for p_file in patch_files:
        ext = p_file.lower().split('.')[-1]
        if ext not in ['bmp', 'bin']:
            continue

        match = re.search(r'screen_(\d+)', p_file.lower())
        if not match:
            continue
            
        target_idx = int(match.group(1)) - 1
        if target_idx >= len(chunks):
            print(f"[警告] {p_file} 編號超過 MKF 極限，跳過。")
            continue

        print(f"正在注入補丁: {os.path.basename(p_file)} (替換索引: {target_idx + 1})...")
        if ext == 'bmp':
            new_chunk = compress_smkf(p_file)
        else: # bin
            with open(p_file, 'rb') as f:
                new_chunk = f.read()
                
        chunks[target_idx] = new_chunk
        patch_count += 1

    if patch_count == 0:
        print(f"資料夾 {patch_dir} 裡面空空如也，沒戲唱。")
        return

    # 重新計算並寫入 MKF
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
            
    print(f"重組完成！共貫穿了 {patch_count} 張圖。趕快丟進遊戲測試！")

if __name__ == "__main__":
    # =========================================================
    # 使用範例 (把你想執行的那行註解拿掉就好)
    # =========================================================

    # 1. 把改好的圖轉成 bin 準備上傳 GitHub (目標 1)
    export_to_bin("SCREEN_19.bmp", "screen_19.bin")

    # 2. 一次把資料夾內所有的補丁(.bmp或.bin)壓進 MKF 裡 (目標 2)
    # 記得先建立一個叫 Patch_Screens 的資料夾，把補丁丟進去
    # batch_patch_mkf("SCREEN.MKF", "Patch_Screens", "SCREEN_NEW.MKF")
    pass