#!/bin/sh

# wget  https://raw.githubusercontent.com/xmayeur/spammon/master/SpamMon.conf
echo  "remove and stop existing container"
docker rm -f spammon
echo "pull the latest version"
docker pull xmayeur/spammon
echo "run the container"
docker run --name spammon --restart always -v /root/:/conf/ -v /var/log:/var/log/ xmayeur/spammon &
sleep 16
echo "bye-bye"