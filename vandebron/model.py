from datetime import datetime

from pydantic import BaseModel


class Location(BaseModel):
    x_coordinate: float
    y_coordinate: float
    knmi_id: str = None


class EDRTenMinutes(BaseModel):
    timestamp: datetime
    dd_10: float
    ff_10m_10: float
    fx_10m_10: float
    p_nap_msl_10: float
    tn_10cm_past_6h_10: float
    t_dryb_10: float
    tn_dryb_10: float
    tx_dryb_10: float
