import tkinter as tk
from tkinter import ttk
import os
import sys
import shutil
import datetime
import subprocess
import re
import ctypes
import io
from contextlib import redirect_stdout

try:
    from lunar_python import Solar
except ImportError:
    print("[ERROR][INIT] 靠背，你還沒裝套件啦！先去終端機跑 pip install lunar_python")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("[ERROR][INIT] 雞歪，少了 PIL 套件！請執行 pip install Pillow")
    sys.exit(1)

# =====================================================================
# 全域 UI 變數與 Log 系統
# =====================================================================
ui_root = None
ui_log_text = None
ui_progress = None


# 暫存資料夾追蹤 (用於毀屍滅跡)
temp_extracted = []
TOTAL_STEPS = 6

def emit_log(msg, step=None, status="INFO"):
    """
    更新終端機輸出，並同步更新 tkinter 介面的進度與文字
    """
    step_tag = f"[STEP {step}/{TOTAL_STEPS}]" if step else "[DETAILS]"
    print(f"[{status}]{step_tag} {msg}", flush=True)

    # 讓 UI 即時更新
    if ui_root and ui_log_text:
        ui_log_text.config(state=tk.NORMAL)          # 開啟編輯模式
        ui_log_text.insert(tk.END, f"[{status}] {msg}\n")  # 插入新訊息到最後一行
        ui_log_text.see(tk.END)                      # 自動滾動到最底下
        ui_log_text.config(state=tk.DISABLED)        # 鎖定編輯模式 (唯讀)
        if step:
            ui_progress['value'] = (step / TOTAL_STEPS) * 100
        ui_root.update()

# =====================================================================
# 資源釋放與清理 (對應 source 2)
# =====================================================================
def extract_bundled_folders(step):
    emit_log("開始檢查並釋放內建資源檔...", step=step)
    bundled_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
    if bundled_dir == os.path.abspath("."):
        emit_log("非 PyInstaller 打包環境，使用本地資料夾。", step=step)
        return

    for folder in ['EVENTVOC', 'NEWSVOC', 'SCREEN']:
        src = os.path.join(bundled_dir, folder)
        dest = os.path.join(os.getcwd(), folder)
        
        if os.path.exists(src):
            if not os.path.exists(dest):
                shutil.copytree(src, dest)
                temp_extracted.append(dest)
                emit_log(f"已釋放資源: {folder}", step=step)
            else:
                shutil.copytree(src, dest, dirs_exist_ok=True)
                emit_log(f"覆寫/更新現有資源: {folder}", step=step)

def cleanup_folders():
    if temp_extracted:
        emit_log("開始執行毀屍滅跡 (清理暫存檔案)...")
        for folder in temp_extracted:
            try:
                shutil.rmtree(folder)
                emit_log(f"已刪除暫存資料夾: {folder}")
            except Exception as e:
                emit_log(f"清理 {folder} 失敗: {e}", status="WARN")

# =====================================================================
# 共用工具 (對應 source 1)
# =====================================================================
def backup_file(filename):
    if not os.path.exists(filename):
        return False
    bak_name = filename + ".bak"
    if not os.path.exists(bak_name):
        shutil.copy2(filename, bak_name)
        emit_log(f"已建立備份 {bak_name}")
    else:
        emit_log(f"{bak_name} 備份已存在，跳過覆蓋以保留最原始檔案")
    return True

# =====================================================================
# 核心處理函數 (對應 source 1, 3, 4)
# =====================================================================
def generate_calendars(step):
    emit_log("開始產生動態滑動日曆 Cald.a 與 Cald.b...", step=step)
    
    # 備份原始日曆檔
    for cald_file in ['Cald.a', 'Cald.b']:
        if os.path.exists(cald_file) and not os.path.exists(f"{cald_file}.bak"):
            shutil.copy2(cald_file, f"{cald_file}.bak")
            emit_log(f"📦 已安全備份原檔: {cald_file} -> {cald_file}.bak")

    now = datetime.datetime.now()
    start_year = now.year - 10
    start_date = datetime.date(start_year, 1, 1)
    total_days = 14612
    end_date = start_date + datetime.timedelta(days=total_days - 1)
    
    emit_log(f"涵蓋範圍：{start_date} 至 {end_date} (共 {total_days} 天)")
    
    a_data = bytearray()
    b_data = bytearray()
    current_date = start_date
    days_count = 0
    
    while current_date <= end_date:
        day, month, year = current_date.day, current_date.month, current_date.year
        a_data.extend(bytes([day, month]) + year.to_bytes(2, byteorder='little'))
        
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        b_data.extend(bytes([lunar.getDay(), abs(lunar.getMonth())]) + lunar.getYear().to_bytes(2, byteorder='little'))
        
        current_date += datetime.timedelta(days=1)
        days_count += 1
        
    with open("Cald.a", "wb") as f: f.write(a_data)
    with open("Cald.b", "wb") as f: f.write(b_data)
        
    emit_log("日曆產生完畢！完美瘦身避免 Buffer Overflow。")
    return days_count

def patch_binary(filename, patches):
    with open(filename, "rb") as f:
        data = f.read()
        
    emit_log(f"開始分析與 Patch {filename} ...")
    modified_data = data
    success_count = 0
    
    for patch in patches:
        name = patch['name']
        success = False
        
        if patch.get('is_regex'):
            pattern = re.compile(patch['pattern'], re.DOTALL)
            if pattern.search(modified_data):
                modified_data = pattern.sub(patch['replacement'], modified_data, count=1)
                success = True
        else:
            for target, replacement in patch['targets']:
                if target in modified_data:
                    if filename.upper().endswith(".MKF"):
                        modified_data = modified_data.replace(target, replacement)
                    else:
                        modified_data = modified_data.replace(target, replacement, 1)
                    success = True
                    break
                
        if success:
            emit_log(f"[成功] {name}")
            success_count += 1
        else:
            emit_log(f"[跳過] {name} (找不到特徵碼或已修改)", status="WARN")
            
    if data != modified_data:
        with open(filename, "wb") as f:
            f.write(modified_data)
        emit_log(f"[完成] {filename} 已儲存修改 ({success_count}/{len(patches)} 項).", status="SUCCESS")
        return True
    else:
        emit_log(f"[提示] {filename} 沒有發生任何變更。", status="WARN")
        return False

def patch_exe(step, total_days):
    emit_log("開始尋找主程式並進行修改...", step=step)
    exe_target = next((name for name in ["RICH3.EXE", "RICH3S.EXE", "rich3.exe", "rich3s.exe"] if os.path.exists(name)), None)
            
    if not exe_target:
        emit_log("找不到 RICH3.EXE 或 RICH3S.EXE！請確認檔案在同目錄。", status="ERROR")
        return False
        
    emit_log(f"找到主程式：{exe_target}")
    backup_file(exe_target)
    
    days_hex = total_days.to_bytes(2, byteorder='little')
    exe_patches = [
        {"name": "多人競賽也可一個人玩", "targets": [(bytes.fromhex("3B 46 C8 7F 0E"), bytes.fromhex("3B 46 C8 90 90"))]},
        {"name": "修正日期二月跳三月問題", "targets": [(bytes.fromhex("75 05 C7 46 EC 1D 00 8B"), bytes.fromhex("75 14 C7 46 EC 1D 00 8B"))]},
        {"name": "修正日曆超過 32KB 無效", "targets": [(bytes.fromhex("48 D1 E0 D1 E0 99"), bytes.fromhex("48 99 D1 E0 D1 E0"))]},
        {
            "name": f"自動變更 CALD.A 搜尋組數 ({total_days} 天)",
            "is_regex": True,
            "pattern": b"\xB9..\xC4\x7E\x0A",
            "replacement": b"\xB9" + days_hex + b"\xC4\x7E\x0A"
        },
        {"name": "命運事件「賣天婦羅」獎金", "targets": [(bytes.fromhex("81 C1 C8 00 83 D3 00"), bytes.fromhex("81 C1 D0 07 83 D3 00"))]},
        {"name": "新聞事件「表彰先進」獎金 (上)", "targets": [
            (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 2C FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 2C FE")),
            (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 2A FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 2A FE")),
            (bytes.fromhex("81 C1 B8 0B 83 D3 00 89 86 34 FE"), bytes.fromhex("81 C1 88 13 83 D3 00 89 86 34 FE"))
        ]},
        {"name": "新聞事件「表彰先進」獎金 (下)", "targets": [
            (bytes.fromhex("C7 86 2E FE DD 01 8D 86 32 FE"), bytes.fromhex("C7 86 2E FE DE 01 8D 86 32 FE")),
            (bytes.fromhex("C7 86 2C FE DD 01 8D 86 30 FE"), bytes.fromhex("C7 86 2C FE DE 01 8D 86 30 FE")),
            (bytes.fromhex("C7 86 36 FE DD 01 8D 86 3A FE"), bytes.fromhex("C7 86 36 FE DE 01 8D 86 3A FE"))
        ]},
        {"name": "修正住院/坐牢免付過路費位置", "targets": [(bytes.fromhex("68 2A 02 68 2A 02"), bytes.fromhex("68 2A 02 68 2C 02"))]},
        {"name": "破解顏色密碼 (磁片版)", "targets": [(bytes.fromhex("83 3E BC 00 02 74 03"), bytes.fromhex("83 3E BC 00 02 EB 03"))]},
        {"name": "破解光碟檢查 (相容項 1)", "targets": [(bytes.fromhex("83 7E EA 06 74 10"), bytes.fromhex("83 7E EA 06 EB 10"))]},
        {"name": "破解光碟檢查 (相容項 2)", "targets": [(bytes.fromhex("0A FF 75 08"), bytes.fromhex("0A FF 90 90"))]},
        {"name": "破解光碟檢查 (相容項 3)", "targets": [(bytes.fromhex("E8 BB 03 EB 2F"), bytes.fromhex("B0 ED 90 EB 2F"))]},
        {"name": "破解光碟檢查 (相容項 4)", "targets": [(bytes.fromhex("56 11 02 00 3A 5C"), bytes.fromhex("56 11 01 00 5C 5C"))]},
        {"name": "破解光碟檢查 (相容項 5)", "targets": [(bytes.fromhex("C4 7E 06 98 AB"), bytes.fromhex("C4 7E 06 90 AB"))]},
    ]
    
    return patch_binary(exe_target, exe_patches)

def patch_map_mkf(step):
    emit_log("開始處理 MAP.MKF 修正物價...", step=step)
    map_target = next((name for name in ["MAP.MKF", "map.mkf"] if os.path.exists(name)), None)
            
    if not map_target:
        emit_log("找不到 MAP.MKF！跳過地圖檔修改。", status="WARN")
        return False
        
    backup_file(map_target)
    map_patches = [
        {"name": "台北新生南路蓋屋 360 -> 3600", "targets": [(bytes.fromhex("FC 08 00 00 10 0E"), bytes.fromhex("FC 08 00 00 68 01"))]},
        {"name": "台北建國北路過路費 2000 -> 200", "targets": [(bytes.fromhex("84 03 00 00 C8 00"), bytes.fromhex("84 03 00 00 D0 07"))]}
    ]
    return patch_binary(map_target, map_patches)

def patch_screen_mkf(step):
    emit_log("開始處理畫面封裝檔 SCREEN.MKF...", step=step)
    orig_mkf_path = next((f for f in os.listdir('.') if f.lower() == 'screen.mkf'), None)
            
    if not orig_mkf_path:
        emit_log("當前目錄找不到 SCREEN.MKF 啦！", status="ERROR")
        return False

    patch_dir = next((d for d in os.listdir('.') if os.path.isdir(d) and d.lower() == 'screen'), None)
    if not patch_dir:
        os.makedirs("screen")
        emit_log("沒找到 screen 資料夾，幫你建一個。有檔案再來跑！", status="WARN")
        return False

    with open(orig_mkf_path, 'rb') as f:
        data = f.read()

    offsets, curr = [], 0
    while curr < len(data):
        offset = int.from_bytes(data[curr:curr+4], byteorder='little')
        offsets.append(offset)
        curr += 4
        if len(offsets) > 1 and curr >= offsets[0]:
            break

    chunks = [data[offsets[i]:offsets[i+1]] for i in range(len(offsets) - 1)]

    def extract_num(filepath):
        match = re.search(r'screen_(\d+)', filepath.lower())
        return int(match.group(1)) if match else 0

    bin_files = sorted([os.path.join(patch_dir, f) for f in os.listdir(patch_dir) if f.lower().endswith('.bin') and re.search(r'screen_(\d+)', f.lower())], key=extract_num)
    patch_count = 0

    for p_file in bin_files:
        target_idx = extract_num(p_file) - 1
        if 0 <= target_idx < len(chunks):
            emit_log(f"注入畫面: {os.path.basename(p_file)} -> 索引 {target_idx + 1}")
            with open(p_file, 'rb') as f:
                chunks[target_idx] = f.read()
            patch_count += 1

    if patch_count == 0:
        emit_log("screen 資料夾沒發現可用的 .bin 檔，白忙一場。", status="WARN")
        return False

    backup_file(orig_mkf_path)
    current_offset = (len(chunks) + 1) * 4
    new_offsets = []
    
    for chunk in chunks:
        new_offsets.append(current_offset)
        current_offset += len(chunk)
    new_offsets.append(current_offset)

    with open(orig_mkf_path, 'wb') as f:
        for off in new_offsets:
            f.write(off.to_bytes(4, byteorder='little'))
        for chunk in chunks:
            f.write(chunk)
            
    emit_log(f"畫面重組完成！共貫穿了 {patch_count} 張。", status="SUCCESS")
    return True

def patch_audio_mkf(target_name, step):
    emit_log(f"開始處理語音封裝檔 {target_name}.MKF...", step=step)
    mkf_path = next((f for f in os.listdir('.') if f.lower() == f"{target_name.lower()}.mkf"), None)
            
    if not mkf_path:
        emit_log(f"找不到 {target_name}.MKF！", status="ERROR")
        return False

    patch_dir = next((d for d in os.listdir('.') if os.path.isdir(d) and d.lower() == target_name.lower()), None)
    if not patch_dir:
        emit_log(f"沒找到 {target_name} 資料夾，跳過。", status="WARN")
        return False

    with open(mkf_path, 'rb') as f:
        data = f.read()

    offsets, curr = [], 0
    while curr < len(data):
        offset = int.from_bytes(data[curr:curr+4], byteorder='little')
        offsets.append(offset)
        curr += 4
        if len(offsets) > 1 and curr >= offsets[0]:
            break

    chunks = [data[offsets[i]:offsets[i+1]] for i in range(len(offsets) - 1)]

    pattern = re.compile(rf"{target_name}_(\d+)\.voc", re.IGNORECASE)
    patch_count = 0
    
    for f in os.listdir(patch_dir):
        match = pattern.search(f)
        if not match: continue
            
        target_idx = int(match.group(1))
        if 0 <= target_idx < len(chunks):
            emit_log(f"注入音檔: {f} -> 索引 {target_idx}")
            with open(os.path.join(patch_dir, f), 'rb') as pf:
                chunks[target_idx] = pf.read()
            patch_count += 1
        else:
            emit_log(f"序數 {target_idx} 超過原始總數，跳過。", status="WARN")

    if patch_count == 0:
        emit_log(f"{target_name} 資料夾無可用檔案，白忙一場。", status="WARN")
        return False

    backup_file(mkf_path)
    current_offset = (len(chunks) + 1) * 4
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
            
    emit_log(f"{mkf_path} 重組完成。替換了 {patch_count} 個音檔。", status="SUCCESS")
    return True

# =====================================================================
# 主幹邏輯 (獨立成一個函數讓 UI 呼叫)
# =====================================================================
def run_patch():
    try:
        # Step 1: 資源釋放
        extract_bundled_folders(step=1)
        
        # Step 2: 產生日曆
        total_days = generate_calendars(step=2)
        
        # Step 3: 修改 EXE
        exe_res = patch_exe(step=3, total_days=total_days)
        
        # Step 4: 修改 MAP
        map_res = patch_map_mkf(step=4)
        
        # Step 5: 修改 SCREEN
        screen_res = patch_screen_mkf(step=5)
        
        # Step 6: 修改 VOC
        voc_news = patch_audio_mkf("NEWSVOC", step=6)
        voc_event = patch_audio_mkf("EVENTVOC", step=6)
        
    except Exception as e:
        err_msg = f"幹，Patch 發生嚴重錯誤：\n{str(e)}"
        emit_log(err_msg, status="FATAL")
        if ui_root:
            ui_root.destroy()
        ctypes.windll.user32.MessageBoxW(0, err_msg, "大富翁3 更新失敗", 0)
        sys.exit(1)

    finally:
        # 無論成功失敗，只要有產生暫存就清掉
        cleanup_folders()

    # 簡單分析成果
    report = []
    report.append("✅ 主程式 (EXE): 成功處理" if exe_res else "⚠️ 主程式 (EXE): 未變動或失敗")
    report.append("✅ 地圖檔 (MAP): 成功處理" if map_res else "⚠️ 地圖檔 (MAP): 未變動或失敗")
    report.append("✅ 畫面檔 (SCREEN): 成功處理" if screen_res else "⚠️ 畫面檔 (SCREEN): 未變動或失敗")
    report.append("✅ 新聞語音 (NEWSVOC): 成功處理" if voc_news else "⚠️ 新聞語音: 未變動或失敗")
    report.append("✅ 事件語音 (EVENTVOC): 成功處理" if voc_event else "⚠️ 事件語音: 未變動或失敗")

    final_msg = "大富翁3 全套 Patch 執行完畢！\n\n【執行摘要】\n" + "\n".join(report)
    emit_log("所有任務完工！爽啦！", step=TOTAL_STEPS, status="DONE")
    
    # 關閉進度條視窗，彈出最終結果
    if ui_root:
        ui_root.destroy()
    ctypes.windll.user32.MessageBoxW(0, final_msg, "大富翁3 更新結果", 0)

def main():
    global ui_root, ui_label, ui_progress
    
    # 建立主視窗
    ui_root = tk.Tk()
    ui_root.title("大富翁3 Patch")
    
    # 設定視窗圖示 (icon.png)
    try:
        # 考慮到 PyInstaller 釋放路徑
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        icon_path = os.path.join(base_path, "icon.png")
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
            photo = tk.PhotoImage(file=icon_path) # 或者用 ImageTk
            ui_root.iconphoto(True, photo)
    except Exception as e:
        print(f"[WARN] 載入圖示失敗，算了不影響功能: {e}")

    # 設定視窗大小與畫面置中
    window_width = 480
    window_height = 280
    screen_width = ui_root.winfo_screenwidth()
    screen_height = ui_root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    ui_root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    # 禁止縮放
    ui_root.resizable(False, False)

    # 進度條
    ui_progress = ttk.Progressbar(ui_root, orient="horizontal", length=380, mode="determinate")
    ui_progress.pack(pady=(15, 10))

    # 建立滾動文字框的 Frame
    log_frame = tk.Frame(ui_root)
    log_frame.pack(padx=15, pady=(0, 15), fill=tk.BOTH, expand=True)

    # 卷軸與 Text 元件
    scrollbar = ttk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    global ui_log_text
    ui_log_text = tk.Text(log_frame, font=("微軟正黑體"), yscrollcommand=scrollbar.set, state=tk.DISABLED, bg="#F0F0F0")
    ui_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=ui_log_text.yview)

    # 設定 0.5 秒後自動開始跑魔改邏輯，讓 UI 有時間先畫出來
    ui_root.after(500, run_patch)

    # 啟動 UI 迴圈
    ui_root.mainloop()

if __name__ == "__main__":
    main()