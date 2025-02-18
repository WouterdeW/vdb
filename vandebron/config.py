import os

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    pg_host: str = os.getenv('PGHOST', 'db')
    username: str = "vdb"
    password: str = "vdbp"
    port: str = "5432"
    db_name: str = "vdb"


class EDRConfig(BaseModel):
    api_key: str = os.getenv("EDR_KEY", "xxx")
    start_datetime: str = os.getenv("START_DATE", "2025-02-17T00:00:00Z")
    location: str = os.getenv("LOCATION", "06260")
    url: str = os.getenv("EDR_URL", "https://api.dataplatform.knmi.nl/edr/v1/collections/observations/locations/")
