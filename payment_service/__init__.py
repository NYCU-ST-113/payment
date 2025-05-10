from dotenv import load_dotenv
import os

# 加載 .env 文件中的環境變量
load_dotenv()

# 現在可以訪問環境變量
smtp_username = os.environ.get("SMTP_USERNAME")
