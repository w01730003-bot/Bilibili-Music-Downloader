@echo off
setlocal enabledelayedexpansion

:menu
cls
echo ===========================================
echo        B站音频下载/合并 自动化工具
echo ===========================================
echo 1. 下载音频 (支持单链、多P、TXT批量)
echo 2. 合并音频 (智能合并并清理分段)
echo 3. 退出
echo.
set /p choice=请输入操作编号: 

if "%choice%"=="1" (
    python bilibili_to_mp3.py
    pause
    goto menu
)
if "%choice%"=="2" (
    python merge_mp3.py
    pause
    goto menu
)
if "%choice%"=="3" exit

goto menu
