import pandas as pd
from functools import lru_cache

class LocDataAccess:
    _instance = None

    @staticmethod
    def get_instance():
        if LocDataAccess._instance is None:
            LocDataAccess()
        return LocDataAccess._instance

    def __init__(self):
        if LocDataAccess._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.df_airports = pd.read_csv('data/geoCrosswalk/GeoCrossWalkMed.csv')
            self.df_airports.set_index('IATA', inplace=True)
            LocDataAccess._instance = self

    @lru_cache(maxsize=None)
    def get_airport_lon_lat_by_iata(self, iata_code):
        if iata_code in self.df_airports.index:
            airport_data = self.df_airports.loc[iata_code]
            return airport_data['Longitude'], airport_data['Latitude']
        else:
            return None, None

    @lru_cache(maxsize=None)
    def get_airport_lon_lat_by_city(self, city_name):
        if city_name is None:
            return None, None
        
        airport_data = self.df_airports[self.df_airports['City'].str.lower() == city_name.lower()]
        if not airport_data.empty:
            return airport_data.iloc[0]['Longitude'], airport_data.iloc[0]['Latitude']
        else:
            return None, None

    @lru_cache(maxsize=None)
    def get_city_by_airport_iata(self, iata_code):
        if iata_code in self.df_airports.index:
            airport_data = self.df_airports.loc[iata_code]
            return airport_data['City']
        else:
            return None

    @lru_cache(maxsize=None)
    def get_country_by_airport_iata(self, iata_code):
        if iata_code in self.df_airports.index:
            airport_data = self.df_airports.loc[iata_code]
            return airport_data['HH_ISO']
        else:
            return None
    
    @lru_cache(maxsize=None)
    def get_country_by_city(self, city_name):
        if city_name is None:
            return None
        airport_data = self.df_airports[self.df_airports['City'].str.lower() == city_name.lower()]
        if not airport_data.empty:
            return airport_data.iloc[0]['HH_ISO']
        else:
            return None
