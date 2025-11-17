#!/bin/bash

source /Users/soonjeongguan/Desktop/Repository/venv/bin/activate
cd /Users/soonjeongguan/Desktop/Repository/CLAUDECODE/NQPV2
PORT=8080 python3 app.py > app_server.log 2>&1
