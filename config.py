import os

class Config:
    # Get the base directory of the current file
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Use the DATABASE_URL environment variable or fallback to SQLite for local testing
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance', 'wrestling.db'))
    
    # Disable FS overhead for SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Use the SECRET_KEY environment variable
    SECRET_KEY = os.getenv('SECRET_KEY')  # Ensure this is set on your production environment
    
    # Other useful configurations
    SEND_FILE_MAX_AGE_DEFAULT = 0

    
