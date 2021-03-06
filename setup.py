from distutils.core import setup

setup(
    name='SpamMon',
    version='0.3',
    packages=[''],
    data_files=[('', ['SpamMon.conf', 'cacert.pem'])],
    url='https://github.com/xmayeur/SpamMon.git',
    license='',
    author='X. Mayeur',
    author_email='xavier@mayeur.be',
    description='eMail Spam monitoring using IMAP',
    requires=['eventlet', 'pycrypto', 'ConfigParser', 'pymysql', 'configobj', 'imapclient']
)
