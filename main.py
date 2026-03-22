import json
import os
import sys
from core import LibraryClient

def get_runtime_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def main():
    config_file = os.path.join(get_runtime_dir(), 'accounts.json')
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print(f"未找到配置文件 '{config_file}'，系统将自动创建一份模板。")
        template = [
            {
                "username": "your_account",
                "password": "your_password"
            }
        ]
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4, ensure_ascii=False)
        print(f"模板已生成，请在 '{config_file}' 中填写真实的账号与密码后重新运行。")
        sys.exit(0)

    # 读取配置文件
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    except json.JSONDecodeError:
        print(f"错误: '{config_file}' 的 JSON 格式不合法，请检查标点符号或引号。")
        sys.exit(1)

    if not isinstance(accounts, list) or not accounts:
        print("错误: 账号列表为空，请在 accounts.json 中添加账号。")
        sys.exit(1)

    # 遍历账号并执行
    print("="*40)
    print(f" 开始执行自动签退程序 - 共计 {len(accounts)} 个账号")
    print("="*40)
    
    for acc in accounts:
        username = acc.get("username")
        password = acc.get("password")
        
        if not username or not password or username == "your_account":
            print(f"跳过无效账号配置: {username}")
            continue
        
        print(f"\n---> 开始处理账号: {username}")
        client = LibraryClient(username, password)
        client.run_auto_checkout()

if __name__ == "__main__":
    main()