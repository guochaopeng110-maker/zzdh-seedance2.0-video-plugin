# -*- coding: utf-8 -*-
import base64
import json
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# 复制 main.py 中的 AuditAESCipher 类
class PluginFatalError(Exception):
    pass

class AuditAESCipher:
    def __init__(self, key_hex):
        try:
            self.key = bytes.fromhex(key_hex)
            if len(self.key) != 32:
                raise ValueError("AES Key 长度必须为 32 字节 (64 位 hex)")
        except Exception as e:
            raise PluginFatalError(f"AES Key 格式错误: {str(e)}")
        self.backend = default_backend()

    def encrypt(self, plaintext):
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.key), modes.ECB(), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt(self, ciphertext_b64):
        ciphertext = base64.b64decode(ciphertext_b64)
        cipher = Cipher(algorithms.AES(self.key), modes.ECB(), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data.decode("utf-8")

def test_encryption():
    # 使用文档中的示例数据（假设一个 key）
    # 文档中的 Python 示例使用 bytes.fromhex("your_64_char_hex_key")
    test_key_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    test_payload = {"images": ["https://example.com/1.jpg"]}
    plaintext = json.dumps(test_payload)
    
    cipher = AuditAESCipher(test_key_hex)
    encrypted = cipher.encrypt(plaintext)
    print(f"Plaintext: {plaintext}")
    print(f"Encrypted (Base64): {encrypted}")
    
    decrypted = cipher.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    assert decrypted == plaintext
    print("Test passed: Encryption and Decryption are symmetrical.")

if __name__ == "__main__":
    test_encryption()
