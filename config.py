import os

class Config:
    # Get the base directory of the current file
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Read database URL from environment variable
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'wrestling.db'))
    
    # Disable FS overhead for SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other useful configurations
    SECRET_KEY = 'a53b32f4238ac0b42700093518c19674a620544082a56ba9'  # Replace with a secure key
    SEND_FILE_MAX_AGE_DEFAULT = 0

