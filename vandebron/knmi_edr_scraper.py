import logging
import sys
from datetime import datetime, timedelta
from typing import Tuple

import dagster as dg
import httpx

from config import DatabaseConfig, EDRConfig
from model import EDRTenMinutes, Location
from repo import Repository

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("vdb")

# These could be replaced by Dagster config.
FLOAT_PARAMS = [
    'dd_10', 'ff_10m_10', 'fx_10m_10', 'p_nap_msl_10',
    'tn_10cm_past_6h_10', 't_dryb_10', 'tn_dryb_10', 'tx_dryb_10'
]
KNMI_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_data() -> dict:
    api_config = EDRConfig()

    headers = {'Authorization': api_config.api_key}
    # We collect the start date and set the end-date to 1 day after the start date.
    start_date = datetime.strptime(api_config.start_datetime, KNMI_DATE_FORMAT)
    params = {'datetime': f'{api_config.start_datetime}/{(start_date + timedelta(days=1)).strftime(KNMI_DATE_FORMAT)}'}

    response = httpx.get(
        url=api_config.url+api_config.location,
        headers=headers,
        params=params,
        follow_redirects=True
    )

    if response.status_code >= 300:
        raise response.raise_for_status()

    return response.json()


def transform_data(raw_data: dict) -> Tuple[Location, list[EDRTenMinutes]]:
    timestamps = raw_data['domain']['axes']['t']['values']
    parameters = {param: raw_data['ranges'][param]['values'] for param in FLOAT_PARAMS}
    length_timestamps = len(timestamps)

    invalid_param_length = []
    for param, values in parameters.items():
        if len(values) != length_timestamps:
            invalid_param_length.append(param)
    if invalid_param_length:
        raise Exception(f"Invalid data received. Invalid amount of values for parameters: {invalid_param_length}")

    logger.info(f"Collected {length_timestamps} rows, all parameters lengths are equal. Validating and transforming "
                f"data...")

    # We validate each 'row' of data to verify that all values are indeed float values. Then we transform the data into
    # a list of EDRTenMinutes objects. That way, we can later easily insert these into the database.
    edr_ten_minutes_data = []
    for i in range(length_timestamps):
        validated_params = [parameters[param][i] if validate_float(param, parameters[param][i]) else None for param in FLOAT_PARAMS]
        edr_data_point = EDRTenMinutes(
            timestamp=timestamps[i],
            dd_10=validated_params[0],
            ff_10m_10=validated_params[1],
            fx_10m_10=validated_params[2],
            p_nap_msl_10=validated_params[3],
            tn_10cm_past_6h_10=validated_params[4],
            t_dryb_10=validated_params[5],
            tn_dryb_10=validated_params[6],
            tx_dryb_10=validated_params[7]
        )
        edr_ten_minutes_data.append(edr_data_point)

    # Since I am now using the 'locations' endpoint, I receive the knmi_id as Identifier in the response.
    # However, I can imagine that we would like to query specific coordinates, and not necessarily a KNMI defined
    # location. I do not know if those queries return an identifier as well.
    try:
        knmi_id = raw_data['inspiregloss:Identifier']
    except KeyError:
        knmi_id = None

    location = Location(
        x_coordinate=raw_data['domain']['axes']['x']['values'][0],
        y_coordinate=raw_data['domain']['axes']['y']['values'][0],
        knmi_id=knmi_id
    )

    return location, edr_ten_minutes_data


def validate_float(parameter_name: str, float_input: float) -> bool:
    try:
        _float_output = float(float_input)
        return True
    except ValueError:
        logger.warning(f"Found a non-float value for parameter {parameter_name}. Skipping value {float_input}")
        return False


def ingest_data(location: Location, edr_ten_minutes_data: list[EDRTenMinutes]):
    logger.info("Ingesting data..")
    database_config = DatabaseConfig()
    repo = Repository(database_config)

    # We first collect the location_id. If this is the first run for this location, the location is stored in the
    # locations table. We then combine the location_id to every line of data we already have. We create a list of
    # dictionaries that is then inserted with the executemany method from psycopg.
    location_id = repo.upsert_location(location=location)
    edr_data = [dict({'location_id': location_id}, **edr.model_dump()) for edr in edr_ten_minutes_data]
    repo.ingest_edr_data(edr_data)
    logger.info("Done!")


@dg.asset
def run():
    raw_data = get_data()
    location, edr_ten_minutes_data = transform_data(raw_data)
    ingest_data(location, edr_ten_minutes_data)


defs = dg.Definitions(assets=[run])

