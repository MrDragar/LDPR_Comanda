import json
import os

from dotenv import load_dotenv

load_dotenv()
VK_API_TOKEN = os.getenv("VK_API_TOKEN")
TG_API_TOKEN = os.getenv("TG_API_TOKEN")
MAX_API_TOKEN = os.getenv("MAX_API_TOKEN")

proxy = os.getenv("PROXY", None)

log_chat = os.getenv("LOG_CHAT")
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE", None)
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
admin_ids = json.loads(os.getenv("ADMIN_IDS", '[]'))
VK_BOT_LINK = os.getenv("VK_BOT_LINK", "https://vk.me/ldpr_bot")
TG_BOT_LINK = os.getenv("TG_BOT_LINK", "https://t.me/ldpr_bot")
MAX_BOT_LINK = os.getenv("MAX_BOT_LINK", "https://max.ru/ldpr_bot")
VERIFY_CHAT_ID = int(os.getenv("VERIFY_CHAT_ID", "0"))
group_id = os.getenv("GROUP_ID")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("S3_REGION", "ru-central1")
S3_KEY = os.getenv("S3_KEY")
S3_SECRET = os.getenv("S3_SECRET")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
