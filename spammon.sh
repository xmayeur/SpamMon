#!/bin/sh

# wget  https://raw.githubusercontent.com/xmayeur/spammon/master/SpamMon.conf

docker run -ti --name spammon --dns 8.8.8.8 -v /root/:/conf/ -v /var/log:/var/log/ spammon

