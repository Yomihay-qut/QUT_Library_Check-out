import requests
import time
import logging
from datetime import datetime, timedelta
from crypto_utils import encrypt_password

# 配置日志输出格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(message)s')

class LibraryClient:
    def __init__(self, username, password):
        self.base_url = "http://10.20.15.27"
        self.username = username
        self.password = password
        self.user_info = {}
        self.session = requests.Session()
        # 初始全局请求头
        self.session.headers.update({
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "lan": "1",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/"
        })
        self.token = None

    def auth(self):
        """执行公钥获取与登录操作"""
        logging.info(f"[{self.username}] 开始执行登录流程...")
        
        # 1. 获取 publicKey、nonceStr 和 ic-cookie
        pub_url = f"{self.base_url}/ic-web/login/publicKey"
        resp1 = self.session.get(pub_url, timeout=10)
        resp1.raise_for_status()
        data1 = resp1.json()
        
        if data1.get("code") != 0:
            raise Exception(f"获取公钥失败: {data1.get('message')}")
        
        pub_key = data1["data"]["publicKey"]
        nonce_str = data1["data"]["nonceStr"]
        # requests.Session() 会自动管理 Set-Cookie 中的 ic-cookie

        # 2. RSA 加密密码
        encrypted_pwd = encrypt_password(self.password, nonce_str, pub_key)

        # 3. 发送登录请求
        login_url = f"{self.base_url}/ic-web/login/user"
        payload = {
            "logonName": self.username,
            "password": encrypted_pwd,
            "captcha": "",
            "consoleType": 16
        }
        resp2 = self.session.post(login_url, json=payload, timeout=10)
        resp2.raise_for_status()
        data2 = resp2.json()
        
        if data2.get("code") != 0:
            raise Exception(f"登录失败: {data2.get('message')}")

        self.user_info = data2.get("data") or {}
        
        # 提取 token 并存入 Session Headers
        self.token = self.user_info.get("token")
        if not self.token:
            raise Exception("登录成功但未获取到token")
        self.session.headers.update({"token": self.token})
        logging.info(f"[{self.username}] 登录成功，已获取身份令牌。")

    def query_reservations(self):
        """查询需签退的预约记录 (needStatus=8454)"""
        logging.info(f"[{self.username}] 开始查询预约记录...")
        today = datetime.now()
        begin_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=6)).strftime("%Y-%m-%d")

        query_url = f"{self.base_url}/ic-web/reserve/resvInfo"
        params = {
            "beginDate": begin_date,
            "endDate": end_date,
            "needStatus": 8454,  # 目前主要用于查询签退目标的固定状态
            "page": 1,
            "pageNum": 10,
            "orderKey": "gmt_create",
            "orderModel": "desc"
        }

        resp = self.session.get(query_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 0:
            raise Exception(f"查询预约失败: {data.get('message')}")
        
        reservations = data.get("data") or []
        logging.info(f"[{self.username}] 查询结束，获取到 {len(reservations)} 条目标预约。")
        return reservations

    def checkout(self, uuid):
        """调用 endAhaed 接口进行提前签退"""
        logging.info(f"[{self.username}] 正在对预约 {uuid} 执行签退...")
        checkout_url = f"{self.base_url}/ic-web/reserve/endAhaed"
        payload = {"uuid": uuid}
        resp = self.session.post(checkout_url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") == 0:
            logging.info(f"[{self.username}] 预约 {uuid} 签退成功！")
        else:
            logging.error(f"[{self.username}] 预约 {uuid} 签退异常: {data.get('message')}")
        return data
        
    def run_auto_checkout(self):
        """完整的自动签退工作流"""
        try:
            self.auth()
            resvs = self.query_reservations()
            success_count = 0
            
            if not resvs:
                logging.info(f"[{self.username}] 没有需要签退的记录。")
                return

            for resv in resvs:
                uuid = resv.get("uuid")
                if uuid:
                    res = self.checkout(uuid)
                    if res.get("code") == 0:
                        success_count += 1
                        time.sleep(1) # 添加少许延迟防并发限流
                        
            logging.info(f"[{self.username}] 执行完毕，本轮成功签退 {success_count} 条记录。")
        except Exception as e:
            logging.error(f"[{self.username}] 工作流被中断: {str(e)}")
