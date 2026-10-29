import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rationsmart-super-secret-key-2026')
    
    # MySQL Database Configuration
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'digital_ration_db')
    
    # 'mysql', 'sqlite', or 'auto'
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    
    # Construct database URIs
    MYSQL_URI = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLITE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'digital_ration.db')}"
    
    # Render and other cloud providers inject DATABASE_URL (often starting with postgres://)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # SQLAlchemy 1.4+ / 2.0 requires postgresql:// instead of legacy postgres://
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif DB_TYPE.lower() == 'mysql':
        SQLALCHEMY_DATABASE_URI = MYSQL_URI
    elif DB_TYPE.lower() == 'sqlite':
        SQLALCHEMY_DATABASE_URI = SQLITE_URI
    else:
        # Default to SQLite for local guarantee
        SQLALCHEMY_DATABASE_URI = SQLITE_URI
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Auto-seed missing demo accounts on startup if database is empty (default True)
    AUTO_SEED_IF_EMPTY = os.environ.get('AUTO_SEED_IF_EMPTY', 'true').lower() in ('true', '1', 'yes')
    
    # Stock alert threshold
    LOW_STOCK_THRESHOLD_DEFAULT = 150.0
    
    # Anomaly detection thresholds
    ANOMALY_RAPID_TRANSACTION_HOURS = 24
    ANOMALY_BULK_MULTIPLIER = 1.5
