from cryptography.fernet import Fernet
import ConfigParser
import getpass

INI_file = 'SpamMon.sh.conf'
key = '6eEwKzh0WQsNYdZWhzyLozc09g-eNDtaRlKm8cnUS3E='

config_file = open(INI_file, 'r+')
config = ConfigParser.SafeConfigParser()
config.readfp(config_file)

#key = Fernet.generate_key()
f = Fernet(key)
pwd= getpass.getpass('Enter a password for SpamMon.sh one.com server: ')
token=f.encrypt(pwd)

config.set('SpamMon.sh', 'password', token)

pwd= getpass.getpass('Enter a password for smtp.gmail.com server: ')
token=f.encrypt(pwd)
config.set('smtp','password', token)


# Writing our configuration file to 'example.cfg'
with open(INI_file, 'wb') as configfile:
    config.write(configfile)