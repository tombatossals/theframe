#!/usr/bin/env bash

#[ -f /home/dave/theframe/completed ] && exit

ping -q -i1 -c4 192.168.4.250 >/dev/null
[ $? -eq 0 ] || exit

source /home/dave/theframe/.venv/bin/activate

IMAGEN=$(find "/home/dave/theframe/painters/" -type f -name "*.jpg" | shuf -n 1)

/home/dave/theframe/process.py "$IMAGEN"
/home/dave/theframe/upload.py /home/dave/dev/theframe/done.jpg

rm -f /home/dave/dev/theframe/done.jpg
#[ $? = 0 ] && touch /home/dave/theframe/completed
