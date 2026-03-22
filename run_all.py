import os
import sys
import shutil
import ctypes  # 召喚 Windows 內建彈跳視窗

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

    # 2. 依序執行 Patch
    try:
        # 注意：如果你的 rich3_patch.py 裡面的函數不叫 main，請自己改掉
        rich3_patch.main() 
        screen_patch.auto_patch_mkf()
        voc_patch.patch_audio_mkf("NEWSVOC")
        voc_patch.patch_audio_mkf("EVENTVOC")
    except Exception as e:
        # 萬一中途噴錯，跳個視窗警告自己
        cleanup_folders()
        ctypes.windll.user32.MessageBoxW(0, f"靠背，Patch 發生錯誤：\n{str(e)}", "大富翁3 更新失敗", 0)
        sys.exit(1)

    # 3. 毀屍滅跡
    cleanup_folders()

    # 4. 成功彈窗 (取代原本的 pause)
    ctypes.windll.user32.MessageBoxW(0, "✅ 所有 Patch 執行完畢！收工！", "大富翁3 更新成功", 0)