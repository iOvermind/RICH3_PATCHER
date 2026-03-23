import os
import sys
import shutil
import ctypes
import io
from contextlib import redirect_stdout

import rich3_patch
import screen_patch
import voc_patch

temp_extracted = []

def extract_bundled_folders():
    bundled_dir = getattr(sys, '_MEIPASS', os.path.abspath("."))
    if bundled_dir == os.path.abspath("."):
        return

    for folder in ['EVENTVOC', 'NEWSVOC', 'SCREEN']:
        src = os.path.join(bundled_dir, folder)
        dest = os.path.join(os.getcwd(), folder)
        
        if os.path.exists(src):
            if not os.path.exists(dest):
                shutil.copytree(src, dest)
                temp_extracted.append(dest) 
            else:
                shutil.copytree(src, dest, dirs_exist_ok=True)

def cleanup_folders():
    if temp_extracted:
        for folder in temp_extracted:
            try:
                shutil.rmtree(folder)
            except Exception:
                pass

if __name__ == '__main__':
    # 1. 釋放資源檔
    extract_bundled_folders()

    # 2. 攔截所有 print 輸出
    log_stream = io.StringIO()
    with redirect_stdout(log_stream):
        try:
            rich3_patch.main() 
            screen_patch.auto_patch_mkf()
            voc_patch.patch_audio_mkf("NEWSVOC")
            voc_patch.patch_audio_mkf("EVENTVOC")
        except Exception as e:
            cleanup_folders()
            ctypes.windll.user32.MessageBoxW(0, f"幹，Patch 發生嚴重錯誤：\n{str(e)}", "大富翁3 更新失敗", 0)
            sys.exit(1)

    # 3. 毀屍滅跡
    cleanup_folders()

    # 4. 分析 Log 並產出報告
    full_log = log_stream.getvalue()
    
    # 順便把 Log 存檔，方便以後抓蟲
    with open("patch_log.txt", "w", encoding="utf-8") as f:
        f.write(full_log)

    # 簡單暴力判斷各個檔案的下場
    report = []
    
    # 判斷 EXE
    if "找不到 RICH3.EXE" in full_log:
        report.append("❌ 主程式 (EXE): 找不到檔案")
    elif "已成功儲存修改" in full_log and ("RICH3" in full_log or "rich3" in full_log):
        report.append("✅ 主程式 (EXE): 成功注入魔改")
    elif "沒有發生任何變更" in full_log and ("RICH3" in full_log or "rich3" in full_log):
        report.append("⚠️ 主程式 (EXE): 已是最新或無變動")
    else:
        report.append("❓ 主程式 (EXE): 狀態不明")

    # 判斷 MAP
    if "找不到 MAP.MKF" in full_log:
        report.append("❌ 地圖檔 (MAP): 找不到檔案")
    elif "已成功儲存修改" in full_log and ("MAP.MKF" in full_log or "map.mkf" in full_log):
        report.append("✅ 地圖檔 (MAP): 成功修正物價")
    elif "沒有發生任何變更" in full_log and ("MAP.MKF" in full_log or "map.mkf" in full_log):
        report.append("⚠️ 地圖檔 (MAP): 已是最新或無變動")
    else:
        report.append("❓ 地圖檔 (MAP): 狀態不明")

    # 判斷 SCREEN
    if "找不到 SCREEN.MKF" in full_log:
        report.append("❌ 畫面檔 (SCREEN): 找不到檔案")
    elif "共貫穿了" in full_log:
        report.append("✅ 畫面檔 (SCREEN): 成功替換圖片")
    else:
        report.append("⚠️ 畫面檔 (SCREEN): 白忙一場或未執行")

    # 判斷 NEWSVOC
    if "找不到 NEWSVOC" in full_log.upper():
        report.append("❌ 新聞語音 (NEWSVOC): 找不到檔案")
    elif "NEWSVOC" in full_log.upper() and "重組完成" in full_log:
        report.append("✅ 新聞語音 (NEWSVOC): 成功替換音檔")
    else:
        report.append("⚠️ 新聞語音 (NEWSVOC): 白忙一場或未執行")

    # 判斷 EVENTVOC
    if "找不到 EVENTVOC" in full_log.upper():
        report.append("❌ 事件語音 (EVENTVOC): 找不到檔案")
    elif "EVENTVOC" in full_log.upper() and "重組完成" in full_log:
        report.append("✅ 事件語音 (EVENTVOC): 成功替換音檔")
    else:
        report.append("⚠️ 事件語音 (EVENTVOC): 白忙一場或未執行")

    final_msg = "大富翁3 Patch 執行完畢！\n詳細紀錄已存入旁邊的 patch_log.txt。\n\n【執行摘要】\n" + "\n".join(report)
    
    # 5. 成功彈窗
    ctypes.windll.user32.MessageBoxW(0, final_msg, "大富翁3 更新結果", 0)