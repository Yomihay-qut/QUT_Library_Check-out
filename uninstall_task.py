import ctypes
import subprocess
import sys


TASK_NAME = "LibraryAutoCheckout"


def task_exists(task_name: str) -> bool:
    """检查计划任务是否存在。"""
    query = subprocess.run(
        f'schtasks /query /tn "{task_name}"',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return query.returncode == 0


def is_admin() -> bool:
    """检查是否拥有管理员权限。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    """若当前非管理员权限，则使用UAC提权重新启动自身。"""
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1,
    )


def uninstall_scheduled_task(task_name: str = TASK_NAME) -> None:
    """删除指定的Windows计划任务。"""
    print(f"正在卸载计划任务: {task_name} ...")
    result = subprocess.run(
        f'schtasks /delete /tn "{task_name}" /f',
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0 and not task_exists(task_name):
        print("\n==================================")
        print("[移除成功] 自动签退计划任务已删除")
        print("==================================")
    else:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout
        if "找不到指定的文件" in message or "cannot find the file" in message.lower():
            print("\n==================================")
            print("[无需处理] 未检测到已安装的计划任务")
            print("==================================")
        else:
            print(f"卸载失败: {message}")
            print("提示: 请以管理员身份运行后重试。")


if __name__ == "__main__":
    print("=========================================")
    print(" 图书馆自动签退 - 卸载工具 (Windows专版)")
    print("=========================================")

    if not is_admin():
        print("检测到当前非管理员权限，正在申请管理员授权...")
        relaunch_as_admin()
        sys.exit(0)

    uninstall_scheduled_task()
    input("\n按回车键退出...")
