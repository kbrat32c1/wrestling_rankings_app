import os

class Config:
    # Get the base directory of the current file
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Path to the SQLite database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'wrestling.db')
    
    # Disable FS overhead for SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other useful configurations
    SECRET_KEY = 'your_secret_key_here'  # Replace with a secure key
    SEND_FILE_MAX_AGE_DEFAULT = 0
