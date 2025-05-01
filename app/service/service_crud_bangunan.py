import time
import random
import io
import csv
from app.repository.repo_crud_bangunan import BangunanRepository

class BangunanService:
    @staticmethod
    def get_all_bangunan(provinsi=None, kota=None, nama=None):
        return BangunanRepository.get_all(provinsi, kota, nama)

    @staticmethod
    def get_bangunan_by_id(bangunan_id):
        return BangunanRepository.get_by_id(bangunan_id)

    @staticmethod
    def create_bangunan(data):
        return BangunanRepository.create(data)

    @staticmethod
    def update_bangunan(bangunan_id, data):
        return BangunanRepository.update(bangunan_id, data)

    @staticmethod
    def delete_bangunan(bangunan_id):
        return BangunanRepository.delete(bangunan_id)

    @staticmethod
    def generate_unique_id(taxonomy: str) -> str:
        if taxonomy not in ("BMN", "FS", "FD"):
            raise ValueError("kode_bangunan invalid, harus BMN/FS/FD")
        while True:
            ts = int(time.time())
            suffix = random.randint(100, 999)
            candidate = f"{taxonomy}_{ts}{suffix}"
            if not BangunanRepository.exists_id(candidate):
                return candidate

    @staticmethod
    def get_provinsi_list():
        return BangunanRepository.get_provinsi_list()

    @staticmethod
    def get_kota_list(provinsi):
        return BangunanRepository.get_kota_list(provinsi)

    @staticmethod
    def upload_csv(file_storage):
        """
        Baca CSV dengan kolom:
          nama_gedung, alamat, provinsi, kota,
          lon, lat,
          kode_bangunan (BMN/FS/FD),
          taxonomy (MUR/MCF/CR/Light Wood),
          luas
        Generate id_bangunan per baris dari kode_bangunan,
        lalu insert tanpa geom (Postgres akan generate geom).
        """
        text = file_storage.stream.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        created = 0

        for row in reader:
            # trim all inputs
            nama     = row.get("nama_gedung","").strip()
            alamat   = row.get("alamat","").strip()
            prov     = row.get("provinsi","").strip()
            kota     = row.get("kota","").strip()
            kode     = row.get("kode_bangunan","").strip()   # BMN/FS/FD
            tax      = row.get("taxonomy","").strip()        # MUR/MCF/CR/Light Wood
            lon      = float(row.get("lon") or 0)
            lat      = float(row.get("lat") or 0)
            luas     = float(row.get("luas") or 0)

            # generate id from kode_bangunan, not taxonomy
            if kode not in ("BMN","FS","FD"):
                raise ValueError(f"Invalid kode_bangunan '{kode}' at line {reader.line_num}")
            data = {
                "id_bangunan": BangunanService.generate_unique_id(kode),
                "nama_gedung": nama,
                "alamat":      alamat,
                "provinsi":    prov,
                "kota":        kota,
                "lon":         lon,
                "lat":         lat,
                "taxonomy":    tax,
                "luas":        luas
            }

            # insert record (geom will be auto‐computed in Postgres)
            BangunanRepository.create(data)
            created += 1

        return {"created": created}