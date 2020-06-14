#!/bin/bash

kill $(ps aux | grep '[y]outubebot.py' | awk '{print $2}')
echo $1
nohup python3.8 youtubebot.py $1 &