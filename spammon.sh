#!/bin/sh

# wget  https://raw.githubusercontent.com/xmayeur/spammon/master/SpamMon.conf

docker run -ti --name spammon -v /root/:/conf/ -v /var/log:/var/log/ xmayeur/spammon

