import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

def encrypt_password(password: str, nonce_str: str, public_key_str: str) -> str:
    """
    模拟前端的 RSA 加密逻辑
    """
    # 1. 按照前端逻辑拼接明文: "密码;随机字符串"
    plaintext = f"{password};{nonce_str}"
    
    # 2. 处理公钥格式 (如果服务器返回的没有头尾，需要手动补全 PEM 格式)
    if "-----BEGIN PUBLIC KEY-----" not in public_key_str:
        public_key_pem = f"-----BEGIN PUBLIC KEY-----\n{public_key_str}\n-----END PUBLIC KEY-----"
    else:
        public_key_pem = public_key_str
        
    try:
        # 3. 导入公钥
        rsa_key = RSA.import_key(public_key_pem)
        
        # 4. 使用 PKCS1_v1_5 填充方式实例化加密器 (与前端 JSEncrypt 行为一致)
        cipher = PKCS1_v1_5.new(rsa_key)
        
        # 5. 执行加密，并将结果转换为 Base64 字符串
        cipher_text = cipher.encrypt(plaintext.encode('utf-8'))
        encrypted_b64 = base64.b64encode(cipher_text).decode('utf-8')
        
        return encrypted_b64
        
    except Exception as e:
        print(f"加密失败，错误信息: {e}")
        return None

# ================= 测试运行 =================
if __name__ == "__main__":
    # 示例占位：请替换为你实时抓包返回的数据
    my_password = "your_plain_password"
    nonce_str = "your_nonce_str"
    public_key = "your_public_key_base64"

    # 执行加密
    encrypted_payload = encrypt_password(my_password, nonce_str, public_key)
    
    print("生成准备提交的密文如下：\n")
    print(encrypted_payload)