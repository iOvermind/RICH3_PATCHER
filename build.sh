#!/bin/bash

echo "=================================="
echo "  [+] Richman 3 Patch Builder Pro"
echo "  [+] Author: Overmind"
echo "=================================="

# 1. 清理舊檔案
echo "[*] Cleaning old files..."
rm -rf build dist

# 2. 建立自簽憑證 (改用 Linux 原生 OpenSSL 產生 PFX，比 Wine 跑 PowerShell 穩太多了)
if [ ! -f "Overmind.pfx" ]; then
    echo "[*] Generating Certificate..."
    # 先產生 key 和 crt
    openssl req -x509 -newkey rsa:2048 -keyout temp_key.pem -out temp_cert.pem -days 3650 -nodes -subj "/CN=Overmind" 2>/dev/null
    # 打包成 pfx，密碼設定為 overmind
    openssl pkcs12 -export -out Overmind.pfx -inkey temp_key.pem -in temp_cert.pem -passout pass:overmind 2>/dev/null
    # 毀屍滅跡
    rm temp_key.pem temp_cert.pem
    echo "[OK] Overmind.pfx created."
fi

# 3. 打包 EXE (透過 Wine 呼叫，並將進入點改為 main.py)
echo "[*] Building EXE with PyInstaller..."
wine python -m PyInstaller --noconsole --onefile \
    --name rich3_patch \
    --icon=icon.png \
    --version-file=file_version_info.txt \
    --add-data "EVENTVOC;EVENTVOC" \
    --add-data "NEWSVOC;NEWSVOC" \
    --add-data "SCREEN;SCREEN" \
    main.py

if [ $? -ne 0 ]; then
    echo "[ERROR] PyInstaller failed! 屁啦，檢查一下 Python 套件。"
    exit 1
fi

# 4. 數位簽章 (放棄 Wine + signtool，改用 Linux 原生 osslsigncode)
echo "[*] Signing the executable..."

# 檢查系統有沒有裝 osslsigncode
if command -v osslsigncode &> /dev/null; then
    # 執行原生簽章
    osslsigncode sign -pkcs12 "Overmind.pfx" -pass "overmind" \
        -n "Richman 3 Patcher" \
        -t http://timestamp.digicert.com \
        -in "dist/rich3_patch.exe" \
        -out "dist/rich3_patch_signed.exe"
    
    if [ $? -eq 0 ]; then
        # 簽章成功就把原本未簽章的覆蓋掉
        mv "dist/rich3_patch_signed.exe" "dist/rich3_patch.exe"
        echo ""
        echo "[DONE] 完工！簽章完美打上，請到 dist 資料夾查看 rich3_patch.exe"
    else
        echo "[WARN] 簽章過程報錯，請檢查憑證或網路連線。"
    fi
else
    echo "[WARN] 靠背，你沒裝 osslsigncode 啦！請先去終端機跑 sudo apt install osslsigncode"
    echo "[DONE] 程式已打包，但未上數位簽章。"
fi