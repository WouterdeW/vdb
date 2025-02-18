CALL refresh_continuous_aggregate('knmi_edr_hourly', '2025-02-01', '2025-02-19');

select * from vdb.knmi_edr_hourly;