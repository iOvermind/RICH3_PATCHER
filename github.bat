@echo off
:: 設定編碼為 UTF-8，防止中文亂碼
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ==========================================
:: 0. 安全設定與解密
:: ==========================================
set GIT_USER=iOvermind
set ENC_FILE=.\tokens\git-token.enc
set REPO_PATH=github.com/iOvermind/RICH3_PATCHER

:: 檢查加密檔是否存在
if not exist "%ENC_FILE%" (
    echo ❌ 找不到加密金鑰檔 ^(%ENC_FILE%^)！
    echo 請確認你是否已將檔案移至 .\tokens\ 並在 .gitignore 加了例外。
    pause
    exit /b 1
)

:: 尋找 OpenSSL (處理 Windows 環境變數可能沒掛載的問題)
set OPENSSL_CMD=openssl
where openssl >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Git\usr\bin\openssl.exe" (
        set OPENSSL_CMD="C:\Program Files\Git\usr\bin\openssl.exe"
    ) else (
        echo ❌ 找不到 OpenSSL！請確認你有安裝 Git for Windows。
        pause
        exit /b 1
    )
)

echo 🔐 請輸入金鑰解鎖密碼:
set /p DEC_PASS="> "

echo ----------------------------------
echo 🐛 [Debug 模式] 準備執行 OpenSSL...
echo ----------------------------------

:: 直接硬碰硬，沒有 2>nul，出錯直接噴在畫面上！
"%OPENSSL_CMD:"=%" enc -d -aes-256-cbc -salt -pbkdf2 -in "%ENC_FILE%" -pass pass:!DEC_PASS! > "%TEMP%\git_token_tmp.txt"

:: 抓 OpenSSL 的真實生死狀態
if !errorlevel! neq 0 (
    echo.
    echo ❌ OpenSSL 陣亡！密碼錯或演算法對不上，請看上方噴了什麼錯。
    del "%TEMP%\git_token_tmp.txt" 2>nul
    set DEC_PASS=
    pause
    exit /b 1
)

:: 確定活著，才去把 Token 挖出來
set /p GIT_TOKEN=<"%TEMP%\git_token_tmp.txt"

:: 擦乾淨屁股
del "%TEMP%\git_token_tmp.txt" 2>nul
set DEC_PASS=

if "!GIT_TOKEN!"=="" (
    echo.
    echo ❌ 靠背，解密說成功，但 Token 竟然是空的！？這見鬼了。
    pause
    exit /b 1
)

echo.
echo 🔓 金鑰解鎖成功！

:: 組合出本次專用的遠端網址
set AUTH_URL=https://%GIT_USER%:!GIT_TOKEN!@%REPO_PATH%.git

:: ==========================================
:: 1. 選單介面
:: ==========================================
echo ==================================
echo    🚀 Git AES-256 傳輸助手 (Windows 專用)
echo    👤 User: %GIT_USER%
echo ==================================
echo 請選擇功能：
echo   [1] ⬇️  下載更新 (Pull)
echo   [2] ⬆️  上傳備份 (Push)
echo ==================================
set /p choice="請輸入選項 [1/2]: "

:: ==========================================
:: 2. 執行邏輯
:: ==========================================
if "%choice%"=="1" (
    echo ----------------------------------
    echo ⬇️  正在從 %REPO_PATH% 拉取...
    git pull "!AUTH_URL!" main
    echo ✅ 下載完成！

) else if "%choice%"=="2" (
    echo ----------------------------------
    echo 📦 正在準備上傳程序...

    :: 檢查是否有 Python 環境才執行 pip freeze
    if exist "requirements.txt" (
        echo 🐍 偵測到 Python 環境，更新 requirements.txt...
        pip freeze > requirements.txt 2>nul
    ) else if exist ".venv\" (
        echo 🐍 偵測到 Python 環境，更新 requirements.txt...
        pip freeze > requirements.txt 2>nul
    )

    :: 加入所有變更
    git add .

    set /p input_msg="請輸入 Commit 訊息 (Enter 自動填時戳): "
    
    if "!input_msg!"=="" (
        :: 呼叫 WMIC 取得不受地區格式影響的精準時間
        for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
        set commit_msg=Auto update: !dt:~0,4!-!dt:~4,2!-!dt:~6,2! !dt:~8,2!:!dt:~10,2!:!dt:~12,2!
    ) else (
        set commit_msg=!input_msg!
    )

    :: 檢查是否有變更
    git diff --quiet && git diff --staged --quiet
    if !errorlevel! equ 0 (
        echo ⚠️  沒有偵測到變更，跳過提交...
    ) else (
        git commit -m "!commit_msg!"
    )

    echo ☁️  正在推送到 %REPO_PATH%...
    git push "!AUTH_URL!" main
    
    if !errorlevel! equ 0 (
        echo ✅ 上傳搞定！收工！
    ) else (
        echo ❌ 上傳失敗！可能是遠端有新內容，請先執行 [1] 下載更新。
    )

) else (
    echo ❌ 選項錯誤。
)

:: 清理變數 (避免金鑰殘留在記憶體)
set GIT_TOKEN=
set AUTH_URL=
echo.
pause