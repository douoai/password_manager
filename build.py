import os
import sys
import subprocess
import shutil

def build_exe():
    print("开始构建可执行文件...")
    
    # 确保在虚拟环境中
    if not os.path.exists(".venv"):
        print("错误：未找到虚拟环境，请先创建虚拟环境")
        return
    
    # 安装必要的包
    print("安装必要的包...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 清理旧的构建文件
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # 构建命令
    build_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "密码管理器",
        "--icon", "icon.ico" if os.path.exists("icon.ico") else None,
        "--add-data", "requirements.txt;.",
        "password_manager.py"
    ]
    
    # 移除 None 值
    build_cmd = [x for x in build_cmd if x is not None]
    
    # 执行构建
    print("执行构建...")
    subprocess.run(build_cmd)
    
    print("构建完成！")
    print("可执行文件位于 dist 目录中")

if __name__ == "__main__":
    build_exe() 