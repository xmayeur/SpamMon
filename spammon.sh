#!/bin/sh
cd ~
docker run -ti --name spammon -v $(pwd):/conf/  xmayeur/spammon:spammon

