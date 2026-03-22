import os
import re
import shutil
from PIL import Image

# =====================================================================
# 大富翁3 專屬 16 色色板 (16.PAT)
# =====================================================================
PALETTE_HEX = "00 00 00 1C 06 01 2B 16 10 3C 26 21 3F 33 2E 3E 3E 3E 31 31 31 19 19 19 00 00 2B 00 2F 37 00 12 00 00 27 00 2F 0C 33 38 00 00 3F 3D 00 1E 22 27"
GAME_PALETTE = bytes.fromhex(PALETTE_HEX.replace(" ", ""))

# =====================================================================
# 壓縮核心邏輯 (保留給未來如果需要 BMP 轉檔時使用)
# =====================================================================
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
# 一條龍補丁注入區
# =====================================================================
def auto_patch_mkf():
    # 1. 不分大小寫尋找當前目錄下的 screen.mkf
    orig_mkf_path = None
    for f in os.listdir('.'):
        if f.lower() == 'screen.mkf':
            orig_mkf_path = f
            break
            
    if not orig_mkf_path:
        print("靠背，當前目錄找不到 SCREEN.MKF 啦！請確認檔案位置。")
        return

    # 2. 不分大小寫尋找 ./screen 資料夾
    patch_dir = None
    for d in os.listdir('.'):
        if os.path.isdir(d) and d.lower() == 'screen':
            patch_dir = d
            break

    if not patch_dir:
        print("沒找到 screen 資料夾，幫你建一個。請把 .bin 檔丟進去後再來跑一次！")
        os.makedirs("screen")
        return

    print(f"[{orig_mkf_path}] 檔案讀取中...")
    with open(orig_mkf_path, 'rb') as f:
        data = f.read()

    # 3. 解析原始 MKF 偏移量
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

    # 4. 撈出所有 .bin 檔並嚴格照數字排序
    bin_files = []
    for f in os.listdir(patch_dir):
        if f.lower().endswith('.bin') and re.search(r'screen_(\d+)', f.lower()):
            bin_files.append(os.path.join(patch_dir, f))

    def extract_num(filepath):
        match = re.search(r'screen_(\d+)', filepath.lower())
        return int(match.group(1)) if match else 0

    bin_files.sort(key=extract_num)
    patch_count = 0

    # 5. 開始注入
    for p_file in bin_files:
        target_idx = extract_num(p_file) - 1
        if target_idx < 0 or target_idx >= len(chunks):
            print(f"[警告] {p_file} 編號超過 MKF 極限 (目前只有 {len(chunks)} 張)，跳過。")
            continue

        print(f"  -> 正在注入: {os.path.basename(p_file)} (替換索引: {target_idx + 1})")
        with open(p_file, 'rb') as f:
            new_chunk = f.read()
            
        chunks[target_idx] = new_chunk
        patch_count += 1

    if patch_count == 0:
        print(f"資料夾 {patch_dir} 裡面沒有符合條件的 .bin 檔，白忙一場。")
        return

    # 6. 備份機制：如果原本就已經有 .bak，會先刪掉再備份，避免 Windows 報錯
    bak_path = orig_mkf_path + '.bak'
    if os.path.exists(bak_path):
        os.remove(bak_path)
    os.rename(orig_mkf_path, bak_path)
    print(f"\n[備份] 已將原檔安全備份為: {bak_path}")

    # 7. 重新計算 Header 並寫入全新 MKF (檔名保持與原檔相同大小寫)
    out_mkf_path = orig_mkf_path
    N = len(chunks)
    current_offset = (N + 1) * 4
    new_offsets = []
    
    for chunk in chunks:
        new_offsets.append(current_offset)
        current_offset += len(chunk)
    new_offsets.append(current_offset)

    print(f"[封裝] 正在重組全新的 {out_mkf_path}...")
    with open(out_mkf_path, 'wb') as f:
        for off in new_offsets:
            f.write(off.to_bytes(4, byteorder='little'))
        for chunk in chunks:
            f.write(chunk)
            
    print(f"爽啦！重組完成。共貫穿了 {patch_count} 張畫面。趕快開遊戲看看會不會當機！")

if __name__ == "__main__":
    auto_patch_mkf()