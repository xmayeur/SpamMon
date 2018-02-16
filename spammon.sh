#!/bin/sh
cd ~
docker run -ti --name spammon -v $(pwd):/conf/  spammon

