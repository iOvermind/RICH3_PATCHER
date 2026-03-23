@echo off
setlocal enabledelayedexpansion

echo ==================================
echo   [+] Richman 3 Patch Builder Pro
echo   [+] Author: Overmind
echo ==================================

:: 1. 清理舊檔案
echo [*] Cleaning old files...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: 2. 建立自簽憑證 (單獨呼叫 PowerShell)
if not exist "Overmind.pfx" (
    echo [*] Generating Certificate...
    powershell -Command "$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=Overmind' -KeyExportPolicy Exportable -KeySpec Signature -KeyLength 2048 -KeyAlgorithm RSA -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(10) -CertStoreLocation 'Cert:\CurrentUser\My'; $pwd = ConvertTo-SecureString -String 'overmind' -Force -AsPlainText; Export-PfxCertificate -Cert $cert -FilePath '.\Overmind.pfx' -Password $pwd"
    echo [OK] Overmind.pfx created.
)

:: 3. 打包 EXE
echo [*] Building EXE with PyInstaller...
:: 這裡加上了 --version-file 和 --uac-admin (改寫檔案需要管理員權限)
python -m PyInstaller --noconsole --onefile ^
    --name rich3_patch ^
    --icon=icon.png ^
    --version-file=file_version_info.txt ^
    --add-data "EVENTVOC;EVENTVOC" ^
    --add-data "NEWSVOC;NEWSVOC" ^
    --add-data "SCREEN;SCREEN" ^
    run_all.py

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed! 屁啦，檢查一下 Python 套件。
    pause
    exit /b
)

:: 4. 數位簽章 (直接使用你找到的路徑)
echo [*] Signing the executable...
set "SIGNTOOL=C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"

if exist "%SIGNTOOL%" (
    "%SIGNTOOL%" sign /f "Overmind.pfx" /p "overmind" /fd SHA256 /t http://timestamp.digicert.com /v "dist\rich3_patch.exe"
) else (
    echo [WARN] 找不到 signtool.exe，跳過簽章。
)

echo.
echo [DONE] 完工！請到 dist 資料夾查看 rich3_patch.exe
pause