# service_directloss.py

import os
import sys
import numpy as np
import pandas as pd
import logging
from app.extensions import db
from app.models.models_database import HasilProsesDirectLoss, HasilAALProvinsi
from app.repository.repo_directloss import get_bangunan_data, get_all_disaster_data

# UTF-8 for console/logging
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Setup logger
DEBUG_DIR = os.path.join(os.getcwd(), "debug_output")
os.makedirs(DEBUG_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.join(DEBUG_DIR, "service_directloss.log"), encoding="utf-8")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)


def process_all_disasters():
    logger.debug("=== START process_all_disasters ===")

    # Clear old
    try:
        db.session.query(HasilProsesDirectLoss).delete()
        db.session.query(HasilAALProvinsi).delete()
        db.session.commit()
        logger.debug("✅ Cleared DirectLoss & AAL")
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Clearing old failed: {e}")

    # 1) Building data (with integer jumlah_lantai)
    bld = get_bangunan_data()
    logger.debug(f"📥 Buildings: {len(bld)} rows")
    bld["jumlah_lantai"] = bld["jumlah_lantai"].fillna(0).astype(int)
    luas  = bld["luas"].fillna(0).to_numpy()
    hsbgn = bld["hsbgn"].fillna(0).to_numpy()

    # 2) Hazard data
    disaster_data = get_all_disaster_data()
    for name, df in disaster_data.items():
        logger.debug(f"📥 {name}: {len(df)} rows")

    # 3) Direct loss calc
    prefix_map = {"gempa":"mmi","banjir":"depth","longsor":"mflux","gunungberapi":"kpa"}
    scales_map = {
      "gempa": ["500","250","100"],
      "banjir": ["100","50","25"],
      "longsor": ["5","2"],
      "gunungberapi": ["250","100","50"]
    }

    for name, df_raw in disaster_data.items():
        if df_raw.empty:
            continue

        pre    = prefix_map[name]
        scales = scales_map[name]

        if name == "banjir":
            floors = np.clip(bld["jumlah_lantai"].to_numpy(), 1, 2)
            for s in scales:
                y1 = df_raw[f"nilai_y_1_{pre}{s}"].fillna(0).to_numpy()
                y2 = df_raw[f"nilai_y_2_{pre}{s}"].fillna(0).to_numpy()
                v = np.where(floors == 1, y1, y2)
                bld[f"direct_loss_{name}_{s}"] = luas * hsbgn * v
                logger.debug(f"direct_loss_banjir_{s} sample: {bld[f'direct_loss_{name}_{s}'].head(3).tolist()}")
        else:
            for s in scales:
                ycols = [
                    f"nilai_y_cr_{pre}{s}",
                    f"nilai_y_mcf_{pre}{s}",
                    f"nilai_y_mur_{pre}{s}",
                    f"nilai_y_lightwood_{pre}{s}"
                ]
                maxv = df_raw[ycols].fillna(0).to_numpy().max(axis=1)
                bld[f"direct_loss_{name}_{s}"] = luas * hsbgn * maxv
                logger.debug(f"direct_loss_{name}_{s} sample: {bld[f'direct_loss_{name}_{s}'].head(3).tolist()}")

    # 4) Save Direct Loss
    dl_cols = [c for c in bld.columns if c.startswith("direct_loss_")]
    mappings = [
        {"id_bangunan": row["id_bangunan"], **{c: row[c] for c in dl_cols}}
        for _, row in bld.iterrows()
    ]
    try:
        db.session.bulk_insert_mappings(HasilProsesDirectLoss, mappings)
        db.session.commit()
        logger.info("✅ Direct Loss saved")
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Saving Direct Loss failed: {e}")
        raise

    # 5) Dump CSV & 6) AAL
    csv_path = os.path.join(DEBUG_DIR, "directloss_all.csv")
    bld.to_csv(csv_path, index=False, sep=';')
    logger.debug(f"📄 CSV DirectLoss: {csv_path}")
    calculate_aal()
    logger.debug("=== END process_all_disasters ===")
    return csv_path


def calculate_aal():
    path = os.path.join(DEBUG_DIR, "directloss_all.csv")
    if not os.path.exists(path):
        logger.error("❌ directloss_all.csv not found")
        return

    df = pd.read_csv(path, delimiter=';')
    periods = {
      "gempa_500":0.02, "gempa_250":0.04, "gempa_100":0.10,
      "banjir_100":0.05,"banjir_50":0.10,"banjir_25":0.20,
      "gunungberapi_250":0.01,"gunungberapi_100":0.03,"gunungberapi_50":0.05,
      "longsor_5":0.02,"longsor_2":0.04
    }

    if "provinsi" not in df or "kode_bangunan" not in df:
        logger.warning("⚠️ Missing provinsi/kode_bangunan")
        return

    grp = df.groupby(["provinsi","kode_bangunan"]).sum()
    aal = pd.DataFrame(index=grp.index)
    for key, p in periods.items():
        dis, sc = key.split("_")
        dlc = f"direct_loss_{dis}_{sc}"
        aalc= f"aal_{dis}_{sc}"
        if dlc in grp:
            aal[aalc] = grp[dlc] * (-np.log(1-p))

    aal.reset_index(inplace=True)
    pivot = aal.pivot(index="provinsi", columns="kode_bangunan")
    pivot.columns = [f"{d}_{b.lower()}" for d,b in pivot.columns]
    pivot.reset_index(inplace=True)

    # total per scale
    for key in periods:
        dis, sc = key.split("_")
        cols = [f"aal_{dis}_{sc}_bmn",f"aal_{dis}_{sc}_fs",f"aal_{dis}_{sc}_fd"]
        exist = [c for c in cols if c in pivot]
        if exist:
            pivot[f"aal_{dis}_{sc}_total"] = pivot[exist].sum(axis=1)

    totals = pivot.select_dtypes(include=[np.number]).sum().to_dict()
    totals["provinsi"] = "Total Keseluruhan"
    final = pd.concat([pivot, pd.DataFrame([totals])], ignore_index=True)

    out = os.path.join(DEBUG_DIR, "AAL_per_provinsi_filtered.csv")
    final.to_csv(out, index=False, sep=';')
    logger.debug(f"📄 CSV AAL: {out}")

    try:
        db.session.query(HasilAALProvinsi).delete()
        mappings = final.to_dict(orient='records')
        db.session.bulk_insert_mappings(HasilAALProvinsi, mappings)
        db.session.commit()
        logger.info("✅ AAL saved")
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Saving AAL failed: {e}")
