from app.core.config import settings
print("MYSQL_URL:", settings.MYSQL_URL)

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(
        settings.MYSQL_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    print("Engine created!")
except Exception as e:
    import traceback
    traceback.print_exc()
