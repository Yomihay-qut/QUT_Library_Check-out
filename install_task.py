import ctypes
import json
import os
import subprocess
import sys
import tempfile

from core import LibraryClient


TASK_NAME = "LibraryAutoCheckout"
TRIGGER_WINDOWS = [
    ("11:20", "PT20M"),  # 11:30 +-10min
    ("17:20", "PT20M"),  # 17:30 +-10min
    ("20:20", "PT20M"),  # 20:30 +-10min
]


def get_runtime_dir() -> str:
    """返回当前程序运行目录：打包后为exe所在目录，源码运行为脚本所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


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
        get_runtime_dir(),
        1,
    )


def _build_trigger_xml() -> str:
    trigger_chunks = []
    for start_time, random_delay in TRIGGER_WINDOWS:
        trigger_chunks.append(
            f"""
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{start_time}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <RandomDelay>{random_delay}</RandomDelay>
    </CalendarTrigger>"""
        )
    return "\n".join(trigger_chunks)


def _load_accounts(accounts_file: str) -> list:
    if not os.path.exists(accounts_file):
        template = [
            {
                "username": "your_account",
                "password": "your_password"
            }
        ]
        try:
            with open(accounts_file, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        raise RuntimeError("未找到 accounts.json，已在当前目录下生模板文件，请先配置真实账号密码后再安装。")

    with open(accounts_file, "r", encoding="utf-8") as f:
        accounts = json.load(f)

    if not isinstance(accounts, list) or not accounts:
        raise RuntimeError("accounts.json 为空，请至少配置一个账号。")

    valid_accounts = []
    for acc in accounts:
        username = (acc or {}).get("username")
        password = (acc or {}).get("password")
        if not username or not password or username == "your_account":
            raise RuntimeError(f"发现无效账号配置: {username}")
        valid_accounts.append((username, password))

    return valid_accounts


def _post_install_verify(accounts_file: str) -> None:
    """安装后立即执行一次登录+查询验证，失败即抛错。"""
    print("\n开始安装后验收：立即执行一次登录与预约查询...")
    valid_accounts = _load_accounts(accounts_file)
    verified_profiles = []

    for username, password in valid_accounts:
        print(f"- 验证账号: {username}")
        client = LibraryClient(username, password)
        client.auth()
        client.query_reservations()
        info = client.user_info or {}
        verified_profiles.append(
            {
                "logon_name": info.get("logonName") or username,
                "true_name": info.get("trueName") or "未知",
                "dept_name": info.get("deptName") or "未知",
                "class_name": info.get("className") or "未知",
                "acc_no": str(info.get("accNo") or "未知"),
            }
        )

    return verified_profiles


def _remove_task(task_name: str) -> None:
    subprocess.run(
        f'schtasks /delete /tn "{task_name}" /f',
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def create_scheduled_task(task_name: str = TASK_NAME) -> bool:
    """创建任务并做安装后验收，只有验收通过才算安装成功。"""
    if task_exists(task_name):
        print("\n==================================")
        print("[安装失败] 已检测到同名计划任务，禁止重复安装")
        print("==================================")
        print(f"任务名: {task_name}")
        print("如需重新安装，请先运行 uninstall_task.py 移除旧任务。")
        return False

    work_dir = get_runtime_dir()
    main_exe_path = os.path.join(work_dir, "main.exe")
    script_path = os.path.join(work_dir, "main.py")
    accounts_file = os.path.join(work_dir, "accounts.json")

    if os.path.exists(main_exe_path):
        command = f'"{main_exe_path}"'
        arguments = ""
    else:
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe
        command = f'"{pythonw_exe}"'
        arguments = f'"{script_path}"'

    user_name = os.environ.get("USERNAME", "")
    computer_name = os.environ.get("COMPUTERNAME", "")
    author = f"{computer_name}\\{user_name}"
    trigger_xml = _build_trigger_xml()

    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>{author}</Author>
    <Description>图书馆自动签退系统后台任务</Description>
  </RegistrationInfo>
  <Triggers>
{trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
            <Command>{command}</Command>
            <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{work_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

    temp_xml = os.path.join(tempfile.gettempdir(), f"{task_name}.xml")
    with open(temp_xml, "w", encoding="utf-16") as f:
        f.write(xml_content)

    try:
        print(f"\n正在向系统注册计划任务：{task_name}...")
        result = subprocess.run(
            f'schtasks /create /tn "{task_name}" /xml "{temp_xml}"',
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 or not task_exists(task_name):
            print(f"安装失败: {result.stderr.strip()}")
            print("提示: 以管理员身份运行后重试。")
            return False

        try:
            verified_profiles = _post_install_verify(accounts_file)
        except Exception as verify_error:
            _remove_task(task_name)
            print("\n==================================")
            print("[安装失败] 安装后即时验收未通过，已自动回滚删除任务")
            print("==================================")
            print(f"失败原因: {verify_error}")
            print("请检查账号密码、网络连通性后重试。")
            return False

        print("\n==================================")
        print("[安装成功] 任务已创建且即时验收通过")
        print("[登录信息] 成功登录并获取您的个人信息！：")
        for profile in verified_profiles:
            print(
                f"- 您的姓名: {profile['true_name']} | 您的学号: {profile['logon_name']} | "
                f"您的账号ID: {profile['acc_no']} | 您的学院: {profile['dept_name']} | 您的班级: {profile['class_name']}"
            )
        print("==================================")
        print("每日触发窗口如下（随机抖动，降低固定时间特征）：")
        print("- 11:30 +-10 分钟")
        print("- 17:30 +-10 分钟")
        print("- 20:30 +-10 分钟")
        print("系统会自动唤醒电脑并在后台静默签退。")
        return True
    finally:
        if os.path.exists(temp_xml):
            os.remove(temp_xml)


if __name__ == "__main__":
    print("=========================================")
    print(" 图书馆自动签退 - 一键部署工具 (Windows专版)")
    print("=========================================")

    if not is_admin():
        print("检测到当前非管理员权限，正在申请管理员授权...")
        relaunch_as_admin()
        sys.exit(0)

    ok = create_scheduled_task()
    input("\n按回车键退出...")
    sys.exit(0 if ok else 1)
