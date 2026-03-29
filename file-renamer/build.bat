@echo off
setlocal enabledelayedexpansion

:: --- 基础配置 ---
set APP_NAME="file_renamer"
set SOURCE_FILE="file_renamer.py"
set VENV_PATH=".venv"
:: -----------------------

echo [*] 正在清理旧的构建产物...
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

echo [*] 正在检查虚拟环境...
:: 自动激活虚拟环境
if exist %VENV_PATH%\Scripts\activate.bat (
    echo [*] 发现虚拟环境，正在激活...
    call %VENV_PATH%\Scripts\activate.bat
) else (
    echo [!] 未发现虚拟环境，将使用系统环境。
)

:: 检查并根据 requirements.txt 安装依赖
if exist "requirements.txt" (
    echo [*] 正在同步依赖库...
    pip install -r requirements.txt
) else (
    echo [!] 未发现 requirements.txt，安装核心组件...
    pip install pyinstaller tkinterdnd2
)

echo [*] 开始执行 PyInstaller 打包 (独立环境模式)...
pyinstaller -F -w --clean --noconfirm ^
    --collect-all tkinterdnd2 ^
    -n %APP_NAME% ^
    %SOURCE_FILE%

:: 检查打包结果
if %errorlevel% equ 0 (
    echo [*] 打包成功！清理临时文件...
    if exist "build" rd /s /q "build"
    if exist "%APP_NAME%.spec" del /q %APP_NAME%.spec
    echo [OK] 最终程序已生成至 dist 文件夹。
) else (
    echo [ERROR] 打包失败，请检查上方报错信息。
)

pause