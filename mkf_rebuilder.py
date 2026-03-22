import os

def pack_mkf(input_dir, output_filename):
    if not os.path.exists(input_dir):
        print(f"[跳過] 幹，找不到資料夾：{input_dir}，你要我壓空氣喔？")
        return

    # 抓取所有檔案並照檔名排序 (確保 file_000, file_001 順序正確)
    files = sorted(os.listdir(input_dir))
    if not files:
        print(f"[跳過] 靠背，{input_dir} 裡面是空的啦！")
        return

    num_files = len(files)
    print(f"[{input_dir}] 抓到 {num_files} 個檔案，準備重新計算索引並打包成 {output_filename}...")

    # MKF 的規則：N 個檔案需要 N+1 個偏移量 (最後一個是 EOF 檔案總長度)
    header_size = (num_files + 1) * 4
    offsets = []
    
    # 初始偏移量就是 Header 的大小
    current_offset = header_size

    # 迴圈計算每個檔案的起點
    file_paths = [os.path.join(input_dir, f) for f in files]
    for path in file_paths:
        offsets.append(current_offset)
        current_offset += os.path.getsize(path)
    
    # 加入最後一個 EOF 偏移量
    offsets.append(current_offset)

    # 開始寫入全新 MKF
    with open(output_filename, 'wb') as f_out:
        # 1. 寫入 Header 索引表 (4 bytes, Little Endian)
        for offset in offsets:
            f_out.write(offset.to_bytes(4, byteorder='little'))
        
        # 2. 依序把檔案二進位資料塞進去
        for path in file_paths:
            with open(path, 'rb') as f_in:
                f_out.write(f_in.read())

    print(f"爽啦！打包完成，新檔案大小：{current_offset} Bytes。")


if __name__ == "__main__":
    # 這裡設定你要打包的資料夾名稱跟輸出的 MKF 檔名
    # 你可以依照實際情況修改
    target_dir = "EVENTVOC_unpacked"
    output_mkf = "EVENTVOC_NEW.MKF"
    
    print("=" * 50)
    pack_mkf(target_dir, output_mkf)
    print("=" * 50)
    print("打包程式執行結束，趕快把檔案丟進遊戲測試會不會當機吧！")