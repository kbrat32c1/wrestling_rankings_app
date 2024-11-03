import os

class Config:
    # Get the base directory of the current file
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Use the DATABASE_URL environment variable for PostgreSQL in production, or fallback to SQLite for local testing
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://ncaa_division_3_wrestlers_user:DEcBFNQcIrsqJCqYGVV0Cm74k35ZtKDY@dpg-csjni9e8ii6s73d67fg0-a.ohio-postgres.render.com/ncaa_division_3_wrestlers_t2mi'
    ) if os.getenv('DATABASE_URL') else 'sqlite:///' + os.path.join(basedir, 'instance', 'wrestling.db')

    # Disable FS overhead for SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Use the SECRET_KEY environment variable, with a fallback for local testing
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')  # Ensure this is set securely in production
    
    # Other useful configurations
    SEND_FILE_MAX_AGE_DEFAULT = 0
