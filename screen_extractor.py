import os
import sys
from PIL import Image

def load_game_palette(pat_path):
    if not os.path.exists(pat_path):
        print(f"幹，找不到色盤檔：{pat_path}")
        sys.exit(1)
        
    with open(pat_path, 'rb') as f:
        data = f.read(48)
        
    flat_palette = []
    for i in range(16):
        flat_palette.extend([data[i*3] << 2, data[i*3 + 1] << 2, data[i*3 + 2] << 2])
    
    flat_palette.extend([0] * (768 - len(flat_palette)))
    return flat_palette

def read_u16(data, offset):
    return int.from_bytes(data[offset:offset+2], byteorder='little')

def get_color_block(color_index):
    b = color_index
    p0 = 0xFF if (b & 1) else 0x00
    p1 = 0xFF if (b & 2) else 0x00
    p2 = 0xFF if (b & 4) else 0x00
    p3 = 0xFF if (b & 8) else 0x00
    return bytes([p0, p1, p2, p3])

def decode_screen_smkf(smkf):
    out = bytearray(32000 * 4) 
    out_pos = 0  
    src_pos = 0  
    smkf_len = len(smkf)
    bg_block = get_color_block(0)

    while src_pos < smkf_len and out_pos < 32000:
        op = smkf[src_pos]

        if op == 0x00:
            break
        elif op == 0x01:
            out[out_pos*4 : out_pos*4+4] = bg_block
            out_pos += 1
            src_pos += 1
        elif op == 0x02:
            c = smkf[src_pos+1]
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = bg_block
                out_pos += 1
            src_pos += 2
        elif op == 0x03:
            c = read_u16(smkf, src_pos+1)
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = bg_block
                out_pos += 1
            src_pos += 3
        elif op == 0x04:
            out[out_pos*4 : out_pos*4+4] = smkf[src_pos+1 : src_pos+5]
            out_pos += 1
            src_pos += 5
        elif op == 0x05:
            # 靠背，這裡原本寫錯。必須以 Grouped Planar 的方式解讀！
            c = smkf[src_pos+1]
            data_len = c * 4
            data = smkf[src_pos+2 : src_pos+2+data_len]
            for i in range(c):
                out[(out_pos + i)*4 + 0] = data[i]
                out[(out_pos + i)*4 + 1] = data[c + i]
                out[(out_pos + i)*4 + 2] = data[2*c + i]
                out[(out_pos + i)*4 + 3] = data[3*c + i]
            out_pos += c
            src_pos += 2 + data_len
        elif op == 0x06:
            # Opcode 6 也是一樣的邏輯錯誤，一併修正
            c = read_u16(smkf, src_pos+1)
            data_len = c * 4
            data = smkf[src_pos+3 : src_pos+3+data_len]
            for i in range(c):
                out[(out_pos + i)*4 + 0] = data[i]
                out[(out_pos + i)*4 + 1] = data[c + i]
                out[(out_pos + i)*4 + 2] = data[2*c + i]
                out[(out_pos + i)*4 + 3] = data[3*c + i]
            out_pos += c
            src_pos += 3 + data_len
        elif op == 0x07:
            b = smkf[src_pos+1]
            c = smkf[src_pos+2]
            col_block = get_color_block(b)
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = col_block
                out_pos += 1
            src_pos += 3
        elif op == 0x08:
            b = smkf[src_pos+1]
            c = read_u16(smkf, src_pos+2)
            col_block = get_color_block(b)
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = col_block
                out_pos += 1
            src_pos += 4
        elif op == 0x09:
            offset = smkf[src_pos+1]
            src = out_pos - offset
            out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
            out_pos += 1
            src_pos += 2
        elif op == 0x0A: 
            offset = smkf[src_pos+1]
            c = smkf[src_pos+2]
            src = out_pos - offset
            block = out[src*4 : src*4+4]
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = block
                out_pos += 1
            src_pos += 3
        elif op == 0x0B: 
            offset = smkf[src_pos+1]
            c = read_u16(smkf, src_pos+2)
            src = out_pos - offset
            block = out[src*4 : src*4+4]
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = block
                out_pos += 1
            src_pos += 4
        elif op == 0x0C: 
            offset = read_u16(smkf, src_pos+1)
            src = out_pos - offset
            out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
            out_pos += 1
            src_pos += 3
        elif op == 0x0D: 
            offset = read_u16(smkf, src_pos+1)
            c = smkf[src_pos+3]
            src = out_pos - offset
            block = out[src*4 : src*4+4]
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = block
                out_pos += 1
            src_pos += 4
        elif op == 0x0E: 
            offset = read_u16(smkf, src_pos+1)
            c = read_u16(smkf, src_pos+3)
            src = out_pos - offset
            block = out[src*4 : src*4+4]
            for _ in range(c):
                out[out_pos*4 : out_pos*4+4] = block
                out_pos += 1
            src_pos += 5
        elif op == 0x0F: 
            offset = smkf[src_pos+1]
            c = smkf[src_pos+2]
            for _ in range(c):
                src = out_pos - offset
                out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
                out_pos += 1
            src_pos += 3
        elif op == 0x10: 
            offset = smkf[src_pos+1]
            c = read_u16(smkf, src_pos+2)
            for _ in range(c):
                src = out_pos - offset
                out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
                out_pos += 1
            src_pos += 4
        elif op == 0x11:
            offset = read_u16(smkf, src_pos+1)
            c = smkf[src_pos+3]
            for _ in range(c):
                src = out_pos - offset
                out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
                out_pos += 1
            src_pos += 4
        elif op == 0x12:
            offset = read_u16(smkf, src_pos+1)
            c = read_u16(smkf, src_pos+3)
            for _ in range(c):
                src = out_pos - offset
                out[out_pos*4 : out_pos*4+4] = out[src*4 : src*4+4]
                out_pos += 1
            src_pos += 5
        elif op == 0x13:
            src_pos += 1
        else:
            print(f"遇到未知的 Opcode: {hex(op)} 位於 {src_pos}")
            break

    return out

def planar_to_pixels(out_buffer, width=640, height=400):
    img = Image.new('P', (width, height))
    pixels = img.load()

    for block_idx in range(width * height // 8):
        y = block_idx // (width // 8)
        base_x = (block_idx % (width // 8)) * 8

        p0 = out_buffer[block_idx*4 + 0]
        p1 = out_buffer[block_idx*4 + 1]
        p2 = out_buffer[block_idx*4 + 2]
        p3 = out_buffer[block_idx*4 + 3]

        for i in range(8):
            bit = 7 - i
            c = ((p0 >> bit) & 1) | \
                (((p1 >> bit) & 1) << 1) | \
                (((p2 >> bit) & 1) << 2) | \
                (((p3 >> bit) & 1) << 3)
            pixels[base_x + i, y] = c
            
    return img

def parse_mkf(mkf_path):
    with open(mkf_path, 'rb') as f:
        data = f.read()

    mkf_len = len(data)
    offsets = []
    curr = 0
    
    while curr < mkf_len:
        offset = int.from_bytes(data[curr:curr+4], byteorder='little')
        offsets.append(offset)
        if offset >= mkf_len:
            break
        curr += 4

    smkf_list = []
    for i in range(len(offsets) - 1):
        smkf_list.append(data[offsets[i]:offsets[i+1]])
        
    return smkf_list

def extract_screens():
    mkf_path = "SCREEN.MKF"
    pat_path = "16.PAT"
    
    if not os.path.exists(mkf_path) or not os.path.exists(pat_path):
        print("請確認 SCREEN.MKF 和 16.PAT 有放在同個目錄底下！")
        return

    flat_palette = load_game_palette(pat_path)
    smkf_list = parse_mkf(mkf_path)
    
    out_dir = "Screens"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"找到 {len(smkf_list)} 張 Screen 準備開炸...")

    for i, smkf in enumerate(smkf_list):
        if not smkf:
            continue
            
        print(f"正在解壓縮 screen_{i+1:02d}.png ...")
        try:
            out_buf = decode_screen_smkf(smkf)
            img = planar_to_pixels(out_buf)
            img.putpalette(flat_palette)
            
            # 把原本存 PNG 的地方改成存 BMP
            out_path = os.path.join(out_dir, f"screen_{i+1:02d}.bmp")
            # 存成 BMP 格式
            img.save(out_path, format="BMP")
        except Exception as e:
            print(f"靠，screen_{i+1:02d} 解析失敗: {e}")

    print("完成！全部螢幕截圖已吐出至 Screens 資料夾！")

if __name__ == "__main__":
    extract_screens()