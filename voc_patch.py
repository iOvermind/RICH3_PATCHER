import os
import re

def patch_audio_mkf(target_name):
    # 1. 不分大小寫找 MKF 原檔
    mkf_path = None
    for f in os.listdir('.'):
        if f.lower() == f"{target_name.lower()}.mkf":
            mkf_path = f
            break
            
    if not mkf_path:
        print(f"[跳過] 當前目錄找不到 {target_name}.MKF！")
        return

    # 2. 不分大小寫找對應的資料夾
    patch_dir = None
    for d in os.listdir('.'):
        if os.path.isdir(d) and d.lower() == target_name.lower():
            patch_dir = d
            break

    if not patch_dir:
        print(f"[跳過] 沒找到 {target_name} 資料夾，請確認後再來！")
        return

    print(f"\n[{mkf_path}] 檔案讀取中，準備開炸...")
    with open(mkf_path, 'rb') as f:
        data = f.read()

    # 解析原始 MKF 的索引偏移量
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

    # 3. 找尋補丁檔案 (嚴格對齊 extractor 的序數)
    pattern = re.compile(rf"{target_name}_(\d+)\.voc", re.IGNORECASE)
    patch_count = 0
    
    for f in os.listdir(patch_dir):
        match = pattern.search(f)
        if not match:
            continue
            
        target_idx = int(match.group(1)) # 直接拿 extractor 給的數字當索引
        p_file = os.path.join(patch_dir, f)
        
        # 防呆：避免數字超標
        if target_idx < 0 or target_idx >= len(chunks):
            print(f"  [警告] 雞歪，{f} 的序數 {target_idx} 超過原始音檔總數 {len(chunks)}，跳過。")
            continue

        print(f"  -> 正在注入: {f} (直接替換索引: {target_idx})")
        with open(p_file, 'rb') as pf:
            chunks[target_idx] = pf.read()
            
        patch_count += 1

    if patch_count == 0:
        print(f"[{target_name}] 資料夾裡沒有符合格式的檔案，白忙一場。")
        return

    # 4. 備份機制
    bak_path = mkf_path + '.bak'
    if os.path.exists(bak_path):
        os.remove(bak_path)
    os.rename(mkf_path, bak_path)
    print(f"  [備份] 已將原檔安全備份為: {bak_path}")

    # 5. 重組並計算全新 Header，寫入新 MKF
    N = len(chunks)
    current_offset = (N + 1) * 4
    new_offsets = []
    
    for chunk in chunks:
        new_offsets.append(current_offset)
        current_offset += len(chunk)
    new_offsets.append(current_offset)

    with open(mkf_path, 'wb') as f:
        for off in new_offsets:
            f.write(off.to_bytes(4, byteorder='little'))
        for chunk in chunks:
            f.write(chunk)
            
    print(f"爽啦！{mkf_path} 重組完成。共精準替換了 {patch_count} 個音檔。")

if __name__ == "__main__":
    print("=== 大富翁3 VOC 音檔精準注入器 ===")
    patch_audio_mkf("NEWSVOC")
    patch_audio_mkf("EVENTVOC")
    print("\n全部作業結束！")