@echo off
:: 設定編碼為 UTF-8
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ==========================================
:: 0. 基本設定 (既然用 SSH，就不用處理 AUTH_URL 了)
:: ==========================================
set REPO_NAME=RICH3_PATCHER

:: ==========================================
:: 1. 選單介面
:: ==========================================
echo ==================================
echo    🚀 Git 自動化助手 (家裡免密碼版)
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
    git pull origin main [cite: 8]
    echo ✅ 下載完成！

) else if "%choice%"=="2" (
    echo ----------------------------------
    echo 📦 正在準備上傳程序...

    :: 檢查是否有 Python 環境 [cite: 5]
    :: 這裡幫你優化了一下：過濾掉本地絕對路徑，避免 requirements.txt 變髒
    if exist "requirements.txt" (
        echo 🐍 偵測到 Python 環境，更新 requirements.txt...
        pip freeze | findstr /v "file:///" > requirements.txt 2>nul [cite: 5]
    ) else if exist ".venv\" (
        echo 🐍 偵測到 Python 環境，更新 requirements.txt...
        pip freeze | findstr /v "file:///" > requirements.txt 2>nul [cite: 5]
    )

    :: 加入所有變更
    git add .
    set /p input_msg="請輸入 Commit 訊息 (Enter 自動填時戳): " [cite: 6]
    
    if "!input_msg!"=="" (
        for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
        set commit_msg=Auto update: !dt:~0,4!-!dt:~4,2!-!dt:~6,2! !dt:~8,2!:!dt:~10,2!:!dt:~12,2! [cite: 6]
    ) else (
        set commit_msg=!input_msg!
    )

    :: 檢查是否有變更 [cite: 7]
    git diff --quiet && git diff --staged --quiet
    if !errorlevel! equ 0 (
        echo ⚠️  沒有偵測到變更，跳過提交... [cite: 7]
    ) else (
        git commit -m "!commit_msg!"
        echo ☁️  正在推送到 GitHub...
        git push origin main [cite: 8]
        
        if !errorlevel! equ 0 (
            echo ✅ 上傳搞定！收工！ [cite: 9]
        ) else (
            echo ❌ 上傳失敗！可能是遠端有新內容，請先執行 [1] 下載更新。 [cite: 9]
        )
    )

) else (
    echo ❌ 選項錯誤。
)

echo.
pause [cite: 10]