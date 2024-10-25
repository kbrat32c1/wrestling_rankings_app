import os

class Config:
    # Get the base directory of the current file
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Read database URL from environment variable
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'wrestling.db'))
    
    # Disable FS overhead for SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Read secret key from environment variable or provide a default (ensure to set it securely in production)
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_default_secret_key_here')
    
    # Other useful configurations
    SEND_FILE_MAX_AGE_DEFAULT = 0
