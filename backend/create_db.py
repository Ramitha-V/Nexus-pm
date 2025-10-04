# This is a one-time setup script
from app.db.models import create_tables

if __name__ == "__main__":
    create_tables()
    
    