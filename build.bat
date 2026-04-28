@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"
title PyQt EXE Template - 打包器

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "MAIN_SCRIPT=script\main.py"
set "APP_NAME=pyqt-exe-template"
set "SETUP_SCRIPT=setup.bat"
set "SPEC_FILE=%APP_NAME%.spec"

echo ========================================
echo   PyQt EXE Template - 打包
echo ========================================
echo.

:: 检查必要文件
if not exist "%SETUP_SCRIPT%" (
    echo [错误] 未找到环境准备脚本：%SETUP_SCRIPT%
    echo.
    pause
    exit /b 1
)

if not exist "%MAIN_SCRIPT%" (
    echo [错误] 未找到主程序：%MAIN_SCRIPT%
    echo.
    pause
    exit /b 1
)

:: 执行环境准备
echo [信息] 检查环境...
call "%SETUP_SCRIPT%"
if errorlevel 1 (
    echo [错误] setup 执行失败，无法继续打包。
    echo.
    pause
    exit /b 1
)

:: 确保 PyInstaller 已安装
echo [信息] 检查 PyInstaller...
"%VENV_PY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [信息] 安装 PyInstaller ...
    "%VENV_PY%" -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] 安装 PyInstaller 失败。
        echo.
        pause
        exit /b 1
    )
)

:: 清理旧的构建文件
echo [信息] 清理旧的构建文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

:: 检查图标文件
set "ICON_PARAM="
if exist "app.ico" (
    echo [信息] 使用应用图标: app.ico
    set "ICON_PARAM=--icon app.ico"
) else (
    echo [警告] 未找到 app.ico，将使用默认图标
)

:: 执行打包
echo [信息] 开始打包...
echo.

if exist "%SPEC_FILE%" (
    echo [信息] 使用现有的 spec 文件: %SPEC_FILE%
    "%VENV_PY%" -m PyInstaller "%SPEC_FILE%" --noconfirm --clean
) else (
    echo [信息] 使用命令行参数打包...
    "%VENV_PY%" -m PyInstaller ^
      --noconfirm ^
      --clean ^
      --onefile ^
      --windowed ^
      --name "%APP_NAME%" ^
      --add-data "resources;resources" ^
      --add-data "config;config" ^
      %ICON_PARAM% ^
      --hidden-import "PyQt6" ^
      --hidden-import "PyQt6.QtCore" ^
      --hidden-import "PyQt6.QtGui" ^
      --hidden-import "PyQt6.QtWidgets" ^
      --hidden-import "yaml" ^
      --hidden-import "requests" ^
      "%MAIN_SCRIPT%"
)

if errorlevel 1 (
    echo.
    echo [错误] PyInstaller 打包失败。
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo [成功] 打包完成！
echo ========================================
echo.
echo 输出文件位置：
echo     dist\%APP_NAME%.exe
echo.

:: 检查输出文件
if exist "dist\%APP_NAME%.exe" (
    echo [信息] 文件大小：
    for %%A in ("dist\%APP_NAME%.exe") do echo     %%~zA 字节
)

echo.
pause

endlocal
exit /b 0
