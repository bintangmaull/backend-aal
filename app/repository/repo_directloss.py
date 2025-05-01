# repo_directloss.py

import os
import pandas as pd
from sqlalchemy import create_engine, text
from app.config import Config

DEBUG_DIR = os.path.join(os.getcwd(), "debug_output")
os.makedirs(DEBUG_DIR, exist_ok=True)

def get_db_connection():
    """Membuat koneksi ke database PostgreSQL."""
    try:
        return create_engine(Config.SQLALCHEMY_DATABASE_URI)
    except Exception as e:
        raise ConnectionError(f"❌ Gagal terhubung ke database: {e}")

def get_bangunan_data():
    """Mengambil data Bangunan lengkap dengan geom, jumlah_lantai (integer), hsbgn & provinsi."""
    query = text("""
        SELECT
            b.id_bangunan,
            b.geom,
            b.luas,
            b.nama_gedung,
            b.alamat,
            b.kode_bangunan,
            b.kota,
            b.jumlah_lantai,           -- langsung ambil integer
            k.provinsi,
            COALESCE(k.hsbgn, 0.0) AS hsbgn
        FROM bangunan b
        LEFT JOIN kota k
          ON b.kota = k.kota;
    """)
    engine = get_db_connection()
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            # Debug: simpan CSV
            df.to_csv(os.path.join(DEBUG_DIR, "debug_bangunan.csv"), index=False, sep=';')
            return df
    except Exception as e:
        raise RuntimeError(f"❌ Kesalahan mengambil data bangunan: {e}")

def get_all_disaster_data():
    """
    Untuk tiap jenis bencana, cari titik model_intensitas_* terdekat
    (berdasarkan geom), lalu join ke dmgratio_* untuk ambil nilai vulnerability.
    """
    mapping = {
      "gempa": {
        "raw": "model_intensitas_gempa",
        "dmgr": "dmgratio_gempa",
        "prefix": "mmi",
        "scales": ["500","250","100"],
        "vcols": lambda pre, s: [
          f"h.dmgratio_cr_{pre}{s}  AS nilai_y_cr_{pre}{s}",
          f"h.dmgratio_mcf_{pre}{s} AS nilai_y_mcf_{pre}{s}",
          f"h.dmgratio_mur_{pre}{s} AS nilai_y_mur_{pre}{s}",
          f"h.dmgratio_lightwood_{pre}{s} AS nilai_y_lightwood_{pre}{s}"
        ]
      },
      "banjir": {
        "raw": "model_intensitas_banjir",
        "dmgr": "dmgratio_banjir_copy",
        "prefix": "depth",
        "scales": ["100","50","25"],
        "vcols": lambda pre, s: [
          f"h.dmgratio_1_{pre}{s} AS nilai_y_1_{pre}{s}",
          f"h.dmgratio_2_{pre}{s} AS nilai_y_2_{pre}{s}"
        ]
      },
      "longsor": {
        "raw": "model_intensitas_longsor",
        "dmgr": "dmgratio_longsor",
        "prefix": "mflux",
        "scales": ["5","2"],
        "vcols": lambda pre, s: [
          f"h.dmgratio_cr_{pre}{s}  AS nilai_y_cr_{pre}{s}",
          f"h.dmgratio_mcf_{pre}{s} AS nilai_y_mcf_{pre}{s}",
          f"h.dmgratio_mur_{pre}{s} AS nilai_y_mur_{pre}{s}",
          f"h.dmgratio_lightwood_{pre}{s} AS nilai_y_lightwood_{pre}{s}"
        ]
      },
      "gunungberapi": {
        "raw": "model_intensitas_gunungberapi",
        "dmgr": "dmgratio_gunungberapi",
        "prefix": "kpa",
        "scales": ["250","100","50"],
        "vcols": lambda pre, s: [
          f"h.dmgratio_cr_{pre}{s}  AS nilai_y_cr_{pre}{s}",
          f"h.dmgratio_mcf_{pre}{s} AS nilai_y_mcf_{pre}{s}",
          f"h.dmgratio_mur_{pre}{s} AS nilai_y_mur_{pre}{s}",
          f"h.dmgratio_lightwood_{pre}{s} AS nilai_y_lightwood_{pre}{s}"
        ]
      }
    }

    engine = get_db_connection()
    all_data = {}

    with engine.connect() as conn:
        for name, cfg in mapping.items():
            raw_table  = cfg["raw"]
            dmgr_table = cfg["dmgr"]
            pre        = cfg["prefix"]
            scales     = cfg["scales"]

            # build vulnerability columns
            cols = []
            for s in scales:
                cols += cfg["vcols"](pre, s)
            col_list = ",\n       ".join(cols)

            query = text(f"""
                SELECT
                  b.id_bangunan,
                  {col_list}
                FROM bangunan b
                LEFT JOIN LATERAL (
                    SELECT id_lokasi
                    FROM {raw_table} r
                    ORDER BY b.geom <-> r.geom
                    LIMIT 1
                ) AS near ON TRUE
                JOIN {dmgr_table} h
                  ON h.id_lokasi = near.id_lokasi;
            """)
            df = pd.read_sql(query, conn)
            df.to_csv(os.path.join(DEBUG_DIR, f"debug_postgres_{name}.csv"),
                      index=False, sep=';')
            all_data[name] = df

    return all_data
