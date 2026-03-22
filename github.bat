@echo off
:: 設定編碼為 UTF-8 [cite: 1]
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ==========================================
:: 0. 基本設定
:: ==========================================
set REPO_NAME=RICH3_PATCHER

:: ==========================================
:: 1. 選單介面
:: ==========================================
echo ==================================
echo    🚀 Git 自動化助手 (家用除錯版)
echo    💻 Repo: %REPO_NAME%
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
    echo ⬇️  正在拉取更新...
    git pull origin main
    echo ✅ 下載完成！

) else if "%choice%"=="2" (
    echo ----------------------------------
    echo 📦 正在準備上傳程序...

    :: 檢查 pip 是否存在並優化輸出 [cite: 5]
    where pip >nul 2>nul
    if !errorlevel! equ 0 (
        if exist "requirements.txt" (
            echo 🐍 偵測到 Python 環境，更新 requirements.txt...
            :: 使用 python -m pip 避免環境變數路徑衝突，並移除 file:/// 絕對路徑
            python -m pip freeze | findstr /v "file:///" > requirements.txt
        )
    )

    :: 加入所有變更
    git add .
    set /p input_msg="請輸入 Commit 訊息 (Enter 自動填時戳): "
    
    if "!input_msg!"=="" (
        :: 捨棄會噴磁碟錯誤的 wmic，改用 PowerShell 抓時間 [cite: 6]
        for /f "usebackq" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set dt=%%i
        set commit_msg=Auto update: !dt!
    ) else (
        set commit_msg=!input_msg!
    )

    :: 檢查是否有變更 [cite: 7]
    git diff --quiet && git diff --staged --quiet
    if !errorlevel! equ 0 (
        echo ⚠️  沒有偵測到變更，跳過提交...
    ) else (
        git commit -m "!commit_msg!"
        echo ☁️  正在推送到 GitHub...
        :: 強制使用 origin main 推送 [cite: 8, 9]
        git push origin main
        
        if !errorlevel! equ 0 (
            echo ✅ 上傳搞定！收工！
        ) else (
            echo ❌ 上傳失敗！請檢查網路或遠端衝突。
        )
    )

) else (
    echo ❌ 選項錯誤。
)

echo.
pause [cite: 10]