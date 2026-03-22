import os
import sys

def is_smkf(data):
    """判定一段二進位資料是否符合 SMKF 二層包裝特徵"""
    if len(data) < 8:
        return False
    num_files = int.from_bytes(data[0:4], byteorder='little')
    first_offset_word = int.from_bytes(data[4:8], byteorder='little')
    
    # 防呆機制：檔案數量不能是 0 或誇張大，且第一個偏移量必須精準等於 N + 2
    if 0 < num_files < 10000 and first_offset_word == num_files + 2:
        return True
    return False

def unpack_mkf_ultimate(file_path):
    if not os.path.exists(file_path):
        print(f"[跳過] 幹，找不到檔案：{file_path}，直接換下一個！")
        return

    # 建立主資料夾
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = f"{base_name}_unpacked_ultimate"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(file_path, 'rb') as f:
        first_offset_bytes = f.read(4)
        if not first_offset_bytes:
            print(f"[跳過] {file_path} 是空檔案！")
            return
            
        first_offset = int.from_bytes(first_offset_bytes, byteorder='little')
        file_size = os.path.getsize(file_path)
        
        if first_offset > file_size or first_offset % 4 != 0:
            print(f"[警告] {file_path} 表頭結構異常，跳過解包。")
            return
            
        num_offsets = first_offset // 4
        f.seek(0)
        offsets = [int.from_bytes(f.read(4), byteorder='little') for _ in range(num_offsets)]
        
        print(f"[{file_path}] 解析到 {num_offsets} 個一級索引，準備啟動一條龍解包...")
        
        smkf_count = 0
        normal_count = 0
        
        for i in range(num_offsets - 1):
            start_pos = offsets[i]
            end_pos = offsets[i+1]
            size = end_pos - start_pos
            
            if size <= 0:
                continue
                
            f.seek(start_pos)
            data = f.read(size)
            
            # 【核心邏輯】當場判定是不是 SMKF 二層結構
            if is_smkf(data):
                num_sub_files = int.from_bytes(data[0:4], byteorder='little')
                print(f"  -> [貫穿] 第 {i:03d} 個檔案是 SMKF 二層包裝！內含 {num_sub_files} 個子檔案，當場拆解！")
                
                # 建立專屬子資料夾
                sub_dir = os.path.join(output_dir, f"file_{i:03d}_smkf")
                os.makedirs(sub_dir, exist_ok=True)
                
                # 計算 SMKF 內部偏移量 (Word * 4)
                sub_offsets = []
                for j in range(num_sub_files + 1):
                    start = 4 + (j * 4)
                    sub_offsets.append(int.from_bytes(data[start:start+4], byteorder='little') * 4)
                    
                # 抽出第三層實體檔案
                for j in range(num_sub_files):
                    s_start = sub_offsets[j]
                    s_end = sub_offsets[j+1]
                    s_size = s_end - s_start
                    if s_size > 0:
                        sub_data = data[s_start:s_end]
                        with open(os.path.join(sub_dir, f"sprite_{j:03d}.dat"), 'wb') as sub_f:
                            sub_f.write(sub_data)
                smkf_count += 1
            else:
                # 一般單層檔案處理
                ext = ".dat"
                if data.startswith(b"Creative Voice File"):
                    ext = ".voc"
                elif data.startswith(b"RIX3"):
                    ext = ".rix"
                
                out_filepath = os.path.join(output_dir, f"file_{i:03d}{ext}")
                with open(out_filepath, "wb") as out_f:
                    out_f.write(data)
                normal_count += 1
                
    print(f"[{file_path}] 一條龍解包完畢！抽出 {normal_count} 個一般檔案，並貫穿了 {smkf_count} 個 SMKF 二層包裝。\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 指定單一檔案
        unpack_mkf_ultimate(sys.argv[1])
    else:
        # 自動掃描當前目錄所有 MKF
        mkf_files = [f for f in os.listdir('.') if f.upper().endswith('.MKF')]
        if not mkf_files:
            print("靠背，沒找到任何 MKF 檔！")
        else:
            for mkf in mkf_files:
                unpack_mkf_ultimate(mkf)
            print("爽啦！全目錄 MKF 一條龍拆解完成。")