import logging
import sys
from datetime import datetime, timedelta

import httpx

from vandebron.config import DatabaseConfig, EDRConfig
from vandebron.model import EDRTenMinutes, Location
from vandebron.repo import Repository

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)

# These could be replaced by a config / env vars.
FLOAT_PARAMS = ['dd_10', 'ff_10m_10', 'fx_10m_10', 'p_nap_msl_10', 'tn_10cm_past_6h_10', 't_dryb_10', 'tn_dryb_10', 'tx_dryb_10']
KNMI_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_data() -> dict:
    api_config = EDRConfig()

    headers = {'Authorization': api_config.api_key}
    start_date = datetime.strptime(api_config.start_datetime, KNMI_DATE_FORMAT)
    params = {'datetime': f'{api_config.start_datetime}/{(start_date + timedelta(days=1)).strftime(KNMI_DATE_FORMAT)}'}
    response = httpx.get(
        url=api_config.url+api_config.location,
        headers=headers,
        params=params,
        follow_redirects=True
    )

    if response.status_code != 200:
        raise response.raise_for_status()

    return response.json()


def transform_data(raw_data: dict):
    timestamps = raw_data['domain']['axes']['t']['values']
    parameters = {param: raw_data['ranges'][param]['values'] for param in FLOAT_PARAMS}
    length_timestamps = len(timestamps)

    invalid_param_length = []
    for param, values in parameters.items():
        if len(values) != length_timestamps:
            invalid_param_length.append(param)
    if invalid_param_length:
        raise Exception(f"Invalid data received. Invalid amount of values for parameters: {invalid_param_length}")

    logging.info(f"Collected {length_timestamps} rows, all parameters lengths are equal. Validating and transforming data...")
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
        logging.warning(f"Found a non-float value for parameter {parameter_name}. Skipping value {float_input}")
        return False


def ingest_data(location: Location, edr_ten_minutes_data: list[EDRTenMinutes]):
    logging.info("Ingesting data..")
    database_config = DatabaseConfig()
    repo = Repository(database_config)
    location_id = repo.upsert_location(location=location)
    edr_location_data = {'location_id': location_id}
    edr_data = [dict(edr_location_data, **edr.model_dump()) for edr in edr_ten_minutes_data]
    repo.ingest_edr_data(edr_data)
    logging.info("Done!")


data = get_data()
location, edr = transform_data(data)
ingest_data(location, edr)
