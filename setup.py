from distutils.core import setup
# from setuptools import find_packages

setup(
    name='SpamMon',
    version='0.2',
    # packages=find_packages(),
    packages=[''],
    data_files=[('',['SpamMon.conf', 'cacert.pem'])],
    # ,('/etc/init.d',['SpamMon.sh'])],
    url='',
    license='',
    author='X. Mayeur',
    author_email='xavier@mayeur.be',
    description='eMail Spam monitoring using IMAP',
    requires=['eventlet', 'cryptography', 'ConfigParser']
)
