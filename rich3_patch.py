import os
import shutil
import datetime
import subprocess
import re

try:
    from lunar_python import Solar
except ImportError:
    print("靠背，你還沒裝套件啦！先去終端機跑 pip install lunar_python")
    exit()

def backup_file(filename):
    if not os.path.exists(filename):
        return False
    bak_name = filename + ".bak"
    if not os.path.exists(bak_name):
        shutil.copy2(filename, bak_name)
        print(f"[備份] 已建立 {bak_name}")
    else:
        print(f"[備份] {bak_name} 已存在，跳過覆蓋以保留最原始檔案")
    return True

def unpack_exe(filename):
    if not os.path.exists("unp.exe"):
        print("\n[脫殼] 跳過自動脫殼 (在同目錄找不到 unp.exe)。")
        return False

    print(f"\n[脫殼] 發現 unp.exe，嘗試解壓縮 {filename}...")
    try:
        result = subprocess.run(["unp.exe", filename], capture_output=True, text=True)
        print(f"[脫殼] unp 執行完畢。\n輸出紀錄: {result.stdout.strip()}")
        return True
    except OSError as e:
        print(f"[脫殼] 提示：執行失敗！如果你的 Windows 不支援 16 位元程式這是正常的，請透過 DOSBox 手動脫殼。\n系統報錯：{e}")
        return False

def generate_calendars():
    now = datetime.datetime.now()
    
    # 動態滑動視窗：從當前年份往前推 10 年，確保這幾年的存檔都能無縫讀取
    start_year = now.year - 10
    start_date = datetime.date(start_year, 1, 1)
    
    # 總天數 14,612 天 (約 40 年)。
    # 確保是 4 的倍數 (16-byte 對齊)，且檔案大小 58,448 Bytes 安全落在 DOS 64KB 限制內，絕不破圖！
    total_days = 14612
    end_date = start_date + datetime.timedelta(days=total_days - 1)
    
    print(f"\n[日曆] 開始產生動態滑動日曆 Cald.a 與 Cald.b")
    print(f"       涵蓋範圍：{start_date} 至 {end_date} (共 {total_days} 天)...")
    
    a_data = bytearray()
    b_data = bytearray()
    
    current_date = start_date
    days_count = 0
    
    while current_date <= end_date:
        # A檔：陽曆 (日 + 月 + 年_2bytes)
        day = current_date.day
        month = current_date.month
        year = current_date.year
        a_data.extend(bytes([day, month]) + year.to_bytes(2, byteorder='little'))
        
        # B檔：農曆 (日 + 月絕對值 + 年_2bytes)
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        b_data.extend(bytes([lunar.getDay(), abs(lunar.getMonth())]) + lunar.getYear().to_bytes(2, byteorder='little'))
        
        current_date += datetime.timedelta(days=1)
        days_count += 1
        
    with open("Cald.a", "wb") as f:
        f.write(a_data)
    with open("Cald.b", "wb") as f:
        f.write(b_data)
        
    print(f"[日曆] 產生完畢！完美瘦身避免 Buffer Overflow。")
    return days_count

def patch_binary(filename, patches):
    with open(filename, "rb") as f:
        data = f.read()
        
    print(f"\n[修改] 開始 Patch {filename} ...")
    modified_data = data
    
    for patch in patches:
        name = patch['name']
        success = False
        
        # 如果設定了正則表示式 (用來處理可能已經被改過無數次的動態 Hex)
        if patch.get('is_regex'):
            pattern = re.compile(patch['pattern'], re.DOTALL)
            if pattern.search(modified_data):
                modified_data = pattern.sub(patch['replacement'], modified_data, count=1)
                success = True
        else:
            # 輪詢固定特徵碼
            for target, replacement in patch['targets']:
                if target in modified_data:
                    # 地圖檔擁有多個同樣的 Bug，允許全局替換；EXE 檔嚴格限制只改第一個
                    if filename.upper().endswith(".MKF"):
                        modified_data = modified_data.replace(target, replacement)
                    else:
                        modified_data = modified_data.replace(target, replacement, 1)
                    success = True
                    break
                
        if success:
            print(f"  [成功] {name}")
        else:
            print(f"  [跳過] {name} (找不到特徵碼，可能版本不同、已改過或檔案未脫殼)")
            
    if data != modified_data:
        with open(filename, "wb") as f:
            f.write(modified_data)
        print(f"[完成] {filename} 已成功儲存修改。")
    else:
        print(f"[提示] {filename} 沒有發生任何變更。")

def main():
    print("=== 大富翁3 (Richman 3) 永續魔改 Patcher ===")
    
    # 1. 產生日曆並取得總天數
    total_days = generate_calendars()
    
    # 2. 處理 EXE
    exe_target = None
    for name in ["RICH3.EXE", "RICH3S.EXE", "rich3.exe", "rich3s.exe"]:
        if os.path.exists(name):
            exe_target = name
            break
            
    if not exe_target:
        print("\n[錯誤] 靠背，找不到 RICH3.EXE 或 RICH3S.EXE！請確認檔案在同目錄。")
    else:
        print(f"\n[偵測] 找到主程式：{exe_target}")
        backup_file(exe_target)
        unpack_exe(exe_target)
        
        days_hex = total_days.to_bytes(2, byteorder='little')
        
        exe_patches = [
            {
                "name": "1. 多人競賽也可一個人玩",
                "targets": [(bytes.fromhex("3B 46 C8 7F 0E"), bytes.fromhex("3B 46 C8 90 90"))]
            },
            {
                "name": "2. 修正日期二月會直接跳到三月的問題",
                "targets": [(bytes.fromhex("75 05 C7 46 EC 1D 00 8B"), bytes.fromhex("75 14 C7 46 EC 1D 00 8B"))]
            },
            {
                "name": "3. 修正日曆檔超過 32KB 資料無效問題",
                "targets": [(bytes.fromhex("48 D1 E0 D1 E0 99"), bytes.fromhex("48 99 D1 E0 D1 E0"))]
            },
            {
                "name": f"4. 自動變更 CALD.A 搜尋組數 (無縫寫入 {total_days} 天)",
                "is_regex": True,
                # 用 Regex 抓取 B9 ?? ?? C4 7E 0A，確保就算 10 年後重新 Patch 也能成功覆寫
                "pattern": b"\xB9..\xC4\x7E\x0A",
                "replacement": b"\xB9" + days_hex + b"\xC4\x7E\x0A"
            },
            {
                "name": "5. 修正命運事件「基隆廟口賣天婦羅」獎金為 2000",
                "targets": [(bytes.fromhex("81 C1 C8 00 83 D3 00"), bytes.fromhex("81 C1 D0 07 83 D3 00"))]
            },
            {
                "name": "6-1. 修正新聞事件「表彰先進個人獎金」為 5000 (上半部)",
                "targets": [
                    (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 2C FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 2C FE")),
                    (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 2A FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 2A FE")),
                    (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 34 FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 34 FE"))
                ]
            },
            {
                "name": "6-2. 修正新聞事件「表彰先進個人獎金」為 5000 (下半部)",
                "targets": [
                    (bytes.fromhex("C7 86 2E FE DD 01 8D 86 32 FE"), bytes.fromhex("C7 86 2E FE DE 01 8D 86 32 FE")),
                    (bytes.fromhex("C7 86 2C FE DD 01 8D 86 30 FE"), bytes.fromhex("C7 86 2C FE DE 01 8D 86 30 FE")),
                    (bytes.fromhex("C7 86 36 FE DD 01 8D 86 3A FE"), bytes.fromhex("C7 86 36 FE DE 01 8D 86 3A FE"))
                ]
            },
            {
                "name": "7. 修正人物住院、坐牢時免付過路費字樣位置錯誤",
                "targets": [(bytes.fromhex("68 2A 02 68 2A 02"), bytes.fromhex("68 2A 02 68 2C 02"))]
            },
            {
                "name": "8-1. 破解顏色密碼 (磁片版)",
                "targets": [(bytes.fromhex("83 3E BC 00 02 74 03"), bytes.fromhex("83 3E BC 00 02 EB 03"))]
            },
            {
                "name": "8-2. 破解光碟檢查 (其餘安全相容項)",
                "targets": [
                    (bytes.fromhex("83 7E EA 06 74 10"), bytes.fromhex("83 7E EA 06 EB 10")),
                    (bytes.fromhex("0A FF 75 08"), bytes.fromhex("0A FF 90 90")), # 如果有人手動改過了，順便修好
                    (bytes.fromhex("E8 BB 03 EB 2F"), bytes.fromhex("B0 ED 90 EB 2F")),
                    (bytes.fromhex("56 11 02 00 3A 5C"), bytes.fromhex("56 11 01 00 5C 5C"))
                ]
            }
        ]
        
        patch_binary(exe_target, exe_patches)

    # 3. Patch MAP.MKF
    map_target = None
    for name in ["MAP.MKF", "map.mkf"]:
        if os.path.exists(name):
            map_target = name
            break
            
    if not map_target:
        print("\n[錯誤] 找不到 MAP.MKF！跳過地圖檔修改。")
    else:
        backup_file(map_target)
        map_patches = [
            {
                "name": "1. 修正台北地圖新生南路蓋屋價 360 變成 3600",
                "targets": [(bytes.fromhex("FC 08 00 00 10 0E"), bytes.fromhex("FC 08 00 00 68 01"))]
            },
            {
                "name": "2. 修正台北地圖建國北路過路費 2000 變成 200",
                "targets": [(bytes.fromhex("84 03 00 00 C8 00"), bytes.fromhex("84 03 00 00 D0 07"))]
            }
        ]
        patch_binary(map_target, map_patches)
        
    print("\n[完工] 永續版魔改作業結束！以後隨時重跑都能自適應！")

if __name__ == "__main__":
    main()