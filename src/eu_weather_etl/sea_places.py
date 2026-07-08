"""Static coastal places monitored by the sea-temperature ETL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeaPlace:
    region: str
    place: str
    country: str
    latitude: float
    longitude: float


SEA_PLACES: tuple[SeaPlace, ...] = (
    SeaPlace("Mediterranean", "Barcelona", "Spain", 41.3730, 2.1880),
    SeaPlace("Mediterranean", "Valencia", "Spain", 39.4561, -0.3076),
    SeaPlace("Mediterranean", "Malaga", "Spain", 36.7213, -4.4213),
    SeaPlace("Mediterranean", "Marseille", "France", 43.2965, 5.3698),
    SeaPlace("Mediterranean", "Nice", "France", 43.6951, 7.2720),
    SeaPlace("Mediterranean", "Genoa", "Italy", 44.4056, 8.9463),
    SeaPlace("Mediterranean", "Naples", "Italy", 40.8333, 14.2500),
    SeaPlace("Mediterranean", "Palermo", "Italy", 38.1157, 13.3615),
    SeaPlace("Mediterranean", "Cagliari", "Italy", 39.2133, 9.1151),
    SeaPlace("Mediterranean", "Split", "Croatia", 43.5081, 16.4402),
    SeaPlace("Mediterranean", "Athens", "Greece", 37.9420, 23.6460),
    SeaPlace("Mediterranean", "Thessaloniki", "Greece", 40.6264, 22.9484),
    SeaPlace("Mediterranean", "Izmir", "Turkey", 38.4192, 27.1287),
    SeaPlace("Mediterranean", "Antalya", "Turkey", 36.8841, 30.7056),
    SeaPlace("Mediterranean", "Alexandria", "Egypt", 31.2001, 29.9187),
    SeaPlace("Mediterranean", "Port Said", "Egypt", 31.2653, 32.3019),
    SeaPlace("Mediterranean", "Tel Aviv", "Israel", 32.0853, 34.7818),
    SeaPlace("Mediterranean", "Beirut", "Lebanon", 33.8938, 35.5018),
    SeaPlace("Mediterranean", "Tripoli", "Libya", 32.8872, 13.1913),
    SeaPlace("Mediterranean", "Tunis", "Tunisia", 36.8065, 10.1815),
    SeaPlace("Mediterranean", "Algiers", "Algeria", 36.7538, 3.0588),
    SeaPlace("Mediterranean", "Oran", "Algeria", 35.6971, -0.6308),
    SeaPlace("Black Sea", "Istanbul", "Turkey", 41.2040, 29.0990),
    SeaPlace("Black Sea", "Varna", "Bulgaria", 43.2141, 27.9147),
    SeaPlace("Black Sea", "Burgas", "Bulgaria", 42.5048, 27.4626),
    SeaPlace("Black Sea", "Constanta", "Romania", 44.1598, 28.6348),
    SeaPlace("Black Sea", "Odesa", "Ukraine", 46.4825, 30.7233),
    SeaPlace("Black Sea", "Sevastopol", "Ukraine", 44.6167, 33.5254),
    SeaPlace("Black Sea", "Novorossiysk", "Russia", 44.7238, 37.7683),
    SeaPlace("Black Sea", "Sochi", "Russia", 43.5853, 39.7203),
    SeaPlace("Black Sea", "Batumi", "Georgia", 41.6423, 41.6418),
    SeaPlace("Black Sea", "Trabzon", "Turkey", 41.0050, 39.7225),
    SeaPlace("Black Sea", "Samsun", "Turkey", 41.2867, 36.3300),
    SeaPlace("Black Sea", "Sinop", "Turkey", 42.0268, 35.1625),
)