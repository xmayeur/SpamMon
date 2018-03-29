#!/bin/sh

git pull
docker rm -f spammon

# sed -i "s/debug = True/debug = False/g" SpamMon.conf

chmod +x *.sh
sudo cp spammon.sh SpamMon.conf /root

docker build -t spammon . && \
docker tag spammon xmayeur/spammon

# docker push xmayeur/spammon

exec ./spammon.sh


