#!/bin/sh

git pull
docker rm -f spammon
docker build -t spammon . && \
docker tag spammon xmayeur\spammon && \
docker push xmayeur/spammon && \
exec ./spammon.sh


