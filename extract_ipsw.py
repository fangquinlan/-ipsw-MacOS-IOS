import os
import glob
import subprocess
import time

def find_ipsw_file():
    """查找当前目录下的IPSW文件"""
    ipsw_files = glob.glob("*.ipsw")
    if not ipsw_files:
        raise FileNotFoundError("未找到IPSW文件")
    return ipsw_files[0]

def run_command(command):
    """执行命令并打印输出"""
    print(f"执行命令: {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 收集所有输出
    stdout, stderr = process.communicate()
    
    # 打印标准输出
    if stdout:
        print(stdout)
    
    # 打印错误输出
    if stderr:
        print("错误输出:", stderr)
            
    if process.returncode != 0:
        print(f"命令执行失败，返回码: {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, command)

def find_files(pattern, base_dir="."):
    """查找文件并返回完整路径"""
    matches = []
    for root, dirnames, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(pattern):
                matches.append(os.path.join(root, filename))
    return matches

def main():
    try:
        # 1. 找到IPSW文件
        ipsw_file = find_ipsw_file()
        print(f"找到IPSW文件: {ipsw_file}")

        # 2. 提取FCS密钥
        run_command(f"ipsw extract --fcs-key {ipsw_file}")
        print("FCS密钥提取完成")
        
        time.sleep(2)
        
        # 3. 提取DMG文件系统
        run_command(f"ipsw extract --dmg fs {ipsw_file}")
        print("DMG文件系统提取完成")
        
        time.sleep(2)
        
        # 4. 查找所有相关文件
        pem_files = find_files(".dmg.aea.pem")
        if not pem_files:
            raise FileNotFoundError("未找到.pem文件")
        print("找到的.pem文件:", pem_files)
        
        aea_files = find_files(".dmg.aea")
        # 只保留直接的.dmg.aea文件，排除.pem和其他扩展文件
        aea_files = [f for f in aea_files if f.endswith('.dmg.aea') and not any(x in f for x in ['mtree', 'root_hash', 'trustcache', 'pem'])]
        if not aea_files:
            raise FileNotFoundError("未找到.dmg.aea文件")
        print("找到的.dmg.aea文件:", aea_files)
        
        # 创建输出目录
        os.makedirs("jiemi", exist_ok=True)
        
        # 5. 直接使用第一个找到的pem和aea文件
        pem_file = os.path.normpath(pem_files[0])
        aea_file = os.path.normpath(aea_files[0])
        
        print(f"\n正在处理:\nPEM: {pem_file}\nAEA: {aea_file}")
        
        # 执行解密命令
        decrypt_cmd = f'ipsw fw aea --pem "{pem_file}" "{aea_file}" --output jiemi'
        try:
            run_command(decrypt_cmd)
            print(f"成功解密: {aea_file}")
        except subprocess.CalledProcessError as e:
            print(f"解密失败: {str(e)}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)