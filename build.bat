@echo off
chcp 65001 >nul
echo ==================================
echo   📦 大富翁 3 Patch 自動打包程式
echo ==================================

:: 1. 清理舊的編譯檔案，確保每次都是乾淨打包
echo 🧹 正在清理舊的暫存檔...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "run_all.spec" del /q "run_all.spec"

:: 2. 執行打包指令
echo 🚀 開始將腳本與資料夾打包成單一 EXE...
pyinstaller --onefile --icon=icon.png --add-data "EVENTVOC;EVENTVOC" --add-data "NEWSVOC;NEWSVOC" --add-data "SCREEN;SCREEN" run_all.py

:: 3. 檢查結果
if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包成功！請去 dist 資料夾裡面拿你的 run_all.exe！
) else (
    echo.
    echo ❌ 靠背，打包失敗！請往上捲看噴了什麼錯。
)

echo.
pause