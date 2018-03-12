import configparser
from base64 import b64encode, b64decode

from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import MD5
from Crypto.PublicKey import RSA


def open_config(f):
    try:
        with open(f, 'r+') as config_file:
            config_ = configparser.SafeConfigParser()
            config_.readfp(config_file)
        return config_
    except IOError:
        return None


def write_config(f, section, option, value):
    config_ = open_config(f)
    if config_ is None:
        config_ = configparser.SafeConfigParser()
    try:
        if not section in config_.sections():
            config_.add_section(section)
        config_.set(section, option, value)
        with open(f, 'w') as f_:
            config_.write(f_)
        return True
    except Exception as e:
        return False


class AEScipher:
    def __init__(self, key=b'My 2nd dog is Lobo!!'):
        self.key = MD5.new(key).digest()
    
    def encrypt(self, text):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return b64encode(iv + cipher.encrypt(text))
    
    def decrypt(self, msg):
        msg = b64decode(msg)
        iv = msg[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return cipher.decrypt(msg[AES.block_size:])
    
    def write_pwd(self, f, section, pwd):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        pwd_ = b64encode(iv + cipher.encrypt(pwd))
        write_config(f, section, 'password', pwd_)
    
    def read_pwd(self, f, section):
        config_ = open_config(f)
        pwd = config_.get(section, 'password')
        msg = b64decode(pwd)
        iv = msg[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return cipher.decrypt(msg[AES.block_size:])


class RSAcipher:
    def __init__(self, certfile):
        self.key = RSA.importKey(open(certfile).read())
        self.rsa = PKCS1_OAEP.new(self.key)
    
    def encrypt(self, text):
        return b64encode(self.rsa.encrypt(text))
    
    def decrypt(self, msg):
        try:
            return self.rsa.decrypt(b64decode(msg))
        except Exception as e:
            return ''


def main():
    text = 'gjlmkslgkfds'
    aes = AEScipher()
    msg = aes.encrypt(text)
    if aes.decrypt(msg) == text:
        print('Successful AES encrypt-decrypt')
    
    aes.write_pwd('pwd.conf', 'PWD', text)
    if aes.read_pwd('pwd.conf', 'PWD') == text:
        print('Successful password store and decode')
    
    # rsa = RSAcipher('xavier_pub.pem')
    # msg = rsa.encrypt(text)
    # rsa = RSAcipher('xavier_priv.pem')
    # if rsa.decrypt(msg) == text:
    #     print 'Successful RSA encrypt-decrypt'


if __name__ == "__main__":
    main()
