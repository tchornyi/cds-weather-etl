"""Static reference data: forecast providers compared by the accuracy ETL.

Each entry is a national/agency weather model exposed through the Open-Meteo
multi-model API (https://open-meteo.com/en/docs), so no API keys are needed.
The "seamless" variants let Open-Meteo pick the best resolution mix offered
by that agency for a given location and lead time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Forecaster:
    model_id: str  # Open-Meteo "models" parameter value
    label: str  # human-readable agency / model name


FORECASTERS: tuple[Forecaster, ...] = (
    Forecaster("best_match", "Open-Meteo Best Match"),
    Forecaster("ecmwf_ifs025", "ECMWF IFS"),
    Forecaster("icon_seamless", "DWD ICON (Germany)"),
    Forecaster("gfs_seamless", "NOAA GFS (USA)"),
    Forecaster("meteofrance_seamless", "Meteo-France ARPEGE/AROME"),
    Forecaster("ukmo_seamless", "UK Met Office"),
    Forecaster("gem_seamless", "ECCC GEM (Canada)"),
    Forecaster("jma_seamless", "JMA (Japan)"),
)
