import os
import secrets
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))

    # Firebase settings
    FIREBASE_PROJECT_ID = 'basketball-academy-baf77'

    # Timezone
    TIMEZONE = pytz.timezone('Asia/Bangkok')

    # Flask settings
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    PORT = int(os.environ.get('PORT', 8080))

    # Pagination
    ITEMS_PER_PAGE = 8

    # Course settings
    CLASSES_PER_COURSE = 8
    PRICE_PER_COURSE = 3000