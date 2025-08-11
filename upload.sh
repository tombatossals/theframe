#!/usr/bin/env sh

cd /home/dave/dev/theframe
source .venv/bin/activate
python main.py upload --embed $*
