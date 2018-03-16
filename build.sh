#!/bin/sh

git pull
docker build -t spammon . && \
docker tag spammon xmayeur\spammon && \
docker push xmayeur/spammon
