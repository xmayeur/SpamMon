#!/bin/sh
cd ~
docker run -ti --name spammon -v $(pwd):/conf/ -v /var/log:/var/log/ xmayeur/spammon:spammon

