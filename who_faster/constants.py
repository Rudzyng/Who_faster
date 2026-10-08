import os

# Адрес API портала Рудзынг.рф.
# Локально задайте переменную окружения LINGVO_API_URL.
API_URL = os.environ.get("LINGVO_API_URL", "http://game.рудзынг.рф/api")

# Ключ сессий flask-приложения. Обязательно переопределить в проде!
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "change-me-in-production")
