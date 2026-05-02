import json
import os

from dotenv import load_dotenv

load_dotenv()
VK_API_TOKEN = os.getenv("VK_API_TOKEN")
TG_API_TOKEN = os.getenv("TG_API_TOKEN")
proxy = os.getenv("PROXY", None)

log_chat = os.getenv("LOG_CHAT")
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", None)
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
admin_ids = json.loads(os.getenv("ADMIN_IDS", '[]'))
