#!/bin/sh

docker run -ti --name spammon -v /root/:/conf/ -v /var/log:/var/log/ xmayeur/spammon

