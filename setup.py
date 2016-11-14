from distutils.core import setup

setup(
    name='SpamMon',
    version='0.2',
    packages=[''],
    data_files=[('',['SpamMon.conf', 'cacert.pem'])],
    url='',
    license='',
    author='X. Mayeur',
    author_email='xavier@mayeur.be',
    description='eMail Spam monitoring using IMAP',
    requires=['eventlet', 'cryptography', 'ConfigParser', 'Key', 'pymysql', 'configobj', 'imapclient']
)
