from app.repository.repo_visualisasi_directloss import GedungRepository


class GedungService:
    @staticmethod
    def get_geojson(bbox=None, prov=None, kota=None):
        return GedungRepository.fetch_geojson(bbox=bbox, prov=prov, kota=kota)

    @staticmethod
    def get_provinsi_list():
        return GedungRepository.fetch_provinsi()

    @staticmethod
    def get_kota_list(provinsi):
        return GedungRepository.fetch_kota(provinsi)
    
# app/service/service_visualisasi_directloss.py

    @staticmethod
    def get_aal_geojson(provinsi=None):
        return GedungRepository.fetch_aal_geojson(provinsi)
    
    @staticmethod
    def get_aal_provinsi_list():
        return GedungRepository.fetch_aal_provinsi_list()

    @staticmethod
    def get_aal_data(provinsi):
        return GedungRepository.fetch_aal_data(provinsi)