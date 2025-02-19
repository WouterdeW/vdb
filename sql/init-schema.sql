CREATE SCHEMA IF NOT EXISTS vdb;

CREATE TABLE IF NOT EXISTS vdb.knmi_edr_locations(
    id              INTEGER         NOT NULL GENERATED ALWAYS AS IDENTITY
,   knmi_id         TEXT
,   name            TEXT
,   x_coordinate    FLOAT           NOT NULL
,   y_coordinate    FLOAT           NOT NULL
,   CONSTRAINT      pk_locations    PRIMARY KEY (id)
,   CONSTRAINT      uq_locations    UNIQUE (x_coordinate, y_coordinate)
);

CREATE TABLE IF NOT EXISTS vdb.knmi_edr_ten_minutes(
    timestamp           TIMESTAMP WITH TIME ZONE    NOT NULL
,   location_id         INTEGER                     NOT NULL
,   dd_10               FLOAT
,   ff_10m_10           FLOAT
,   fx_10m_10           FLOAT
,   p_nap_msl_10        FLOAT
,   tn_10cm_past_6h_10  FLOAT
,   t_dryb_10           FLOAT
,   tn_dryb_10          FLOAT
,   tx_dryb_10          FLOAT
,   inserted_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
,   CONSTRAINT          fk_knmi_edr FOREIGN KEY (location_id) REFERENCES vdb.knmi_edr_locations(id)
,   CONSTRAINT          uq_knmi_edr_ten_minutes UNIQUE (timestamp, location_id)
);

SELECT create_hypertable(
  relation               => 'vdb.knmi_edr_ten_minutes'
, time_column_name       => 'timestamp'
, chunk_time_interval    => interval '1 day'
);

CREATE MATERIALIZED VIEW IF NOT EXISTS vdb.knmi_edr_hourly
            WITH (timescaledb.continuous, timescaledb.materialized_only = true, timescaledb.create_group_indexes=false) AS
SELECT  time_bucket('1 hour', timestamp) AS hour_bucket
,       location_id
,       AVG(dd_10)  AS dd_10
,       AVG(ff_10m_10)  AS ff_10m_10
,       AVG(fx_10m_10)  AS fx_10m_10
,       AVG(p_nap_msl_10)   AS p_nap_msl_10
,       AVG(tn_10cm_past_6h_10) AS tn_10cm_past_6h_10
,       AVG(t_dryb_10)  AS t_dryb_10
,       AVG(tn_dryb_10) AS tn_dryb_10
,       AVG(tx_dryb_10) AS tx_dryb_10
FROM vdb.knmi_edr_ten_minutes
GROUP BY hour_bucket, location_id
WITH NO DATA;

CREATE INDEX IF NOT EXISTS hourly_readings on vdb.knmi_edr_hourly (location_id, hour_bucket);

SELECT add_continuous_aggregate_policy('knmi_edr_hourly',
                                       start_offset => INTERVAL '1 month',
                                       end_offset => INTERVAL '12 h',
                                       schedule_interval => INTERVAL '10 m');
