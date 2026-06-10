from app.core.database import Base, engine
# Import all models here so that Base has them registered before create_all()
from app.database.models import *

def init_db():
    """Create all tables in the MySQL database."""
    Base.metadata.create_all(bind=engine)
