import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

def encrypt_password(password: str, nonce_str: str, public_key_str: str) -> str:
    """
    模拟前端的 RSA 加密逻辑
    """
    # 按照前端逻辑拼接明文: "密码;随机字符串"
    plaintext = f"{password};{nonce_str}"
    
    # 处理公钥格式
    if "-----BEGIN PUBLIC KEY-----" not in public_key_str:
        public_key_pem = f"-----BEGIN PUBLIC KEY-----\n{public_key_str}\n-----END PUBLIC KEY-----"
    else:
        public_key_pem = public_key_str
        
    try:
        # 导入公钥
        rsa_key = RSA.import_key(public_key_pem)
        
        # 使用 PKCS1_v1_5 填充方式实例化加密器
        cipher = PKCS1_v1_5.new(rsa_key)
        
        # 执行加密，并将结果转换为 Base64 字符串
        cipher_text = cipher.encrypt(plaintext.encode('utf-8'))
        encrypted_b64 = base64.b64encode(cipher_text).decode('utf-8')
        
        return encrypted_b64
        
    except Exception as e:
        raise ValueError(f"RSA加密失败: {e}")
