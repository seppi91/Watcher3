#!/usr/bin/env python3
# ======================================== #
# ============= INSTRUCTIONS ============= #

# Add file to QBittorrent's Run External Program
# python "path/to/this/script/qbittorrent.py" "%N" "%D" "%R" "%I"

# Add api information to conf:

watcherapi = "APIKEY"
watcheraddress = "http://localhost:9090/"
category = "Watcher"
verifyssl = True  # may need to change to False if using self-signed ssl cert

#  DO NOT TOUCH ANYTHING BELOW THIS LINE!  #
# ======================================== #

import json
import os
import ssl
import sys


download_dir = sys.argv[2]  # %D

while download_dir[-1] in ("/", "\\"):
    download_dir = download_dir[:-1]
parent_folder = os.path.split(download_dir)[-1]
if parent_folder.lower() != category.lower():
    # Not watcher category
    sys.exit(0)


if sys.version_info.major < 3:
    import urllib
    import urllib2

    urlencode = urllib.urlencode
    request = urllib2.Request
    urlopen = urllib2.urlopen
else:
    import urllib.parse
    import urllib.request

    request = urllib.request.Request
    urlencode = urllib.parse.urlencode
    urlopen = urllib.request.urlopen

ctx = ssl.create_default_context()
if not verifyssl:
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

# Gather info
data = {}

data["apikey"] = watcherapi

data["name"] = sys.argv[1]  # %N
data["path"] = sys.argv[3]  # %R
data["downloadid"] = sys.argv[4]  # %I
data["guid"] = sys.argv[4]
data["mode"] = "complete"

# Send info
url = u"{}/postprocessing/".format(watcheraddress)
post_data = urlencode(data).encode("ascii")

request = request(url, post_data, headers={"User-Agent": "Mozilla/5.0"})
response = json.loads(urlopen(request, timeout=600, context=ctx).read().decode("utf-8"))

if response["status"] == "finished":
    sys.exit(0)
elif response["status"] == "incomplete":
    sys.exit(1)
else:
    sys.exit(1)

sys.exit(0)

# pylama:ignore=E402
