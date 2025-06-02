@echo off
echo 正在启动构建过程...

REM 检查虚拟环境
if not exist .venv (
    echo 创建虚拟环境...
    python -m venv .venv
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 运行构建脚本
python build.py

REM 暂停以查看输出
pause 