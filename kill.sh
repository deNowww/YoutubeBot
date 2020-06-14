#!/bin/bash

kill $(ps aux | grep '[y]outubebot.py' | awk '{print $2}')