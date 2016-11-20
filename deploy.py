from py_compile import compile
from time import sleep

from fabric.api import *

env.host_string = 'rpiMON'
env.user = 'pi'
env.use_ssh_config = True

# Deploy files
deploy_list = ['spam.py', 'SpamMon.py']
script = 'SpamMon'

for f in deploy_list:
    if f.find('.py') > 0:
        compile(f)
        put(local_path=f + 'c', remote_path='~/SpamMon/' + f + 'c')
    else:
        put(local_path=f, remote_path='~/SpamMon/' + f)

# Stop service, update it and re-start
with settings(warn_only=True):
    run('sudo service ' + script + ' stop')

with cd('/etc/init.d'):
    put(local_path=script + '.', remote_path='/etc/init.d/' + script, use_sudo=True, mode=0755)
    run('sudo update-rc.d ' + script + ' defaults')

run('sudo service ' + script + ' start')
sleep(5)
run('sudo service ' + script + ' status')
