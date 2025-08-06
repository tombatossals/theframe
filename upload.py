#!/usr/bin/env python

import sys
import os
import logging
import wakeonlan
from datetime import datetime
from samsungtvws import SamsungTVWS
from dotenv import load_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()  # take environment variables from .env.

filename=sys.argv[1]
tv = SamsungTVWS(host=os.getenv("TV_ADDRESS"), port=8002, token_file=os.getenv("TV_TOKEN"))


file = open(f'{filename}', 'rb')
data = file.read()
uploadedID = tv.art().upload(data, file_type="JPEG", matte='none')
tv.art().select_image(uploadedID, show=tv.art().get_artmode() == "on")

# Delete old images
try:
    current_img = tv.art().get_current()
except Exception as e:
    pass

info = tv.art().available()
ids = [ i.get("content_id") for i in info if i.get("content_id") != current_img.get("content_id")]
tv.art().delete_list(ids)
