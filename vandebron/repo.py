import logging
import sys

import psycopg

from config import DatabaseConfig
from model import Location

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)


class Repository:
    def __init__(self, config: DatabaseConfig):
        self._config = config

    def _connect(self):
        return psycopg.connect(
            f'host={self._config.pg_host} '
            f'port={self._config.port} '
            f'dbname={self._config.db_name} '
            f'user={self._config.username} '
            f'password={self._config.password}'
        )

    def upsert_location(self, location: Location) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vdb.knmi_edr_locations (
                        knmi_id,
                        x_coordinate,
                        y_coordinate
                    ) VALUES (
                        %(knmi_id)s,
                        %(x_coordinate)s,
                        %(y_coordinate)s
                    )
                    ON CONFLICT(x_coordinate, y_coordinate) DO UPDATE SET 
                    x_coordinate=excluded.x_coordinate,
                    y_coordinate=excluded.y_coordinate
                    RETURNING id
                    """, location.model_dump()
                )
                res = cur.fetchone()
                return res[0]

    def ingest_edr_data(self, edr_data: list[dict]):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO vdb.knmi_edr_ten_minutes (
                        timestamp,
                        location_id,         
                        dd_10,               
                        ff_10m_10,           
                        fx_10m_10,           
                        p_nap_msl_10,        
                        tn_10cm_past_6h_10,  
                        t_dryb_10,           
                        tn_dryb_10,          
                        tx_dryb_10
                    ) VALUES (
                        %(timestamp)s,
                        %(location_id)s,
                        %(dd_10)s,
                        %(ff_10m_10)s,
                        %(fx_10m_10)s,
                        %(p_nap_msl_10)s,
                        %(tn_10cm_past_6h_10)s,
                        %(t_dryb_10)s,
                        %(tn_dryb_10)s,
                        %(tx_dryb_10)s
                    ) ON CONFLICT DO NOTHING     
                    """, edr_data
                )


