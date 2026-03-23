@echo off
echo ==================================
echo   [+] Richman 3 Patch Builder
echo ==================================

:: 1. Clean old files
echo [*] Cleaning old temp files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "run_all.spec" del /q "run_all.spec"
if exist "rich3_patch.spec" del /q "rich3_patch.spec"

:: 2. Build EXE
echo [*] Building EXE...
python -m PyInstaller --noconsole --onefile --name rich3_patch --icon=icon.png --add-data "EVENTVOC;EVENTVOC" --add-data "NEWSVOC;NEWSVOC" --add-data "SCREEN;SCREEN" run_all.py

:: 3. Check result
if %errorlevel% equ 0 (
    echo.
    echo [OK] Build SUCCESS! Check the 'dist' folder.
) else (
    echo.
    echo [ERROR] Build FAILED! Check the error messages above.
)

echo.
pause