@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

cd /d "%~dp0"
title PyQt EXE Template - 环境安装器

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_CFG=%VENV_DIR%\pyvenv.cfg"
set "REQUIREMENTS=requirements.txt"
set "SNAPSHOT_FILE=%VENV_DIR%\.requirements.snapshot"
set "PYTHON_VERSION=3.12"

echo ========================================
echo   PyQt EXE Template - 环境准备
echo ========================================
echo.

:: 检查 py 启动器
where py >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 py 启动器。
    echo 请先安装 Python %PYTHON_VERSION%，并确保勾选 Python Launcher。
    echo.
    pause
    exit /b 1
)

:: 检查指定 Python 版本
py -%PYTHON_VERSION% -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python %PYTHON_VERSION%。
    echo 请先安装 Python %PYTHON_VERSION%。
    echo.
    pause
    exit /b 1
)

:: 创建虚拟环境
if not exist "%VENV_PY%" (
    echo [信息] 未检测到虚拟环境，正在创建...
    py -%PYTHON_VERSION% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        echo.
        pause
        exit /b 1
    )
)

:: 验证虚拟环境版本
set "VENV_VER="
if exist "%VENV_CFG%" (
    for /f "tokens=1,* delims==" %%A in (%VENV_CFG%) do (
        set "KEY=%%A"
        set "VAL=%%B"
        set "KEY=!KEY: =!"
        if /i "!KEY!"=="version" (
            set "VENV_VER=!VAL!"
            set "VENV_VER=!VENV_VER: =!"
        )
    )
)

echo [信息] 当前虚拟环境版本：%VENV_VER%
echo %VENV_VER% | findstr /b "%PYTHON_VERSION%." >nul
if errorlevel 1 (
    echo [警告] 当前虚拟环境不是 Python %PYTHON_VERSION%，正在重建...
    rmdir /s /q "%VENV_DIR%"
    py -%PYTHON_VERSION% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [错误] 重建虚拟环境失败。
        echo.
        pause
        exit /b 1
    )
)

:: 升级基础工具
echo [信息] 升级 pip / setuptools / wheel ...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [错误] 升级基础工具失败。
    echo.
    pause
    exit /b 1
)

:: 安装依赖
if exist "%REQUIREMENTS%" (
    echo [信息] 正在安装 requirements.txt 中的依赖...
    "%VENV_PY%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo [错误] 安装 requirements.txt 依赖失败。
        echo.
        pause
        exit /b 1
    )
    copy /y "%REQUIREMENTS%" "%SNAPSHOT_FILE%" >nul
) else (
    echo [警告] 未找到 requirements.txt
    pause
    exit /b 1
)

echo.
echo [成功] 环境准备完成。
echo.
endlocal
exit /b 0
