import requests
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("PMG_USERNAME") + "@pmg"  # adjust realm
PASSWORD = os.getenv("PMG_PASSWORD")
HOSTS = os.getenv("PMG_HOSTS").split(",")
VERIFY_SSL = os.getenv("PMG_VERIFY_SSL", "true").lower() == "true"

for host in HOSTS:
    url = f"https://{host}/api2/json/access/ticket"
    resp = requests.post(url, data={"username": USERNAME, "password": PASSWORD}, verify=VERIFY_SSL)
    print(host, resp.status_code, resp.text)