from fabric.api import *
# from py_compile import compile

env.host_string = 'rpiMON'
env.user = 'pi'
env.use_ssh_config = True

# Deploy files
deploy_list = ['spam.py', 'SpamMon.py']
script = 'SpamMon'

with cd('~/SpamMon'):
    for f in deploy_list:
        put(f)

# Stop service, update it and re-start
with settings(warn_only=True):
    run('sudo service ' + script + ' stop')

with cd('/etc/init.d'):
    put(local_path=script + '.', remote_path='/etc/init.d/' + script, use_sudo=True, mode=0755)
    run('sudo update-rc.d ' + script + ' defaults')

run('sudo service ' + script + ' start')
