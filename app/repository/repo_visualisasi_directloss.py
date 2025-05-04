from sqlalchemy import text
from app.extensions import db
import io

class GedungRepository:
    @staticmethod
    def fetch_geojson(bbox=None, prov=None, kota=None):
        where = ["1=1"]
        params = {}

        if bbox:
            west, south, east, north = map(float, bbox.split(","))
            where.append(
              "b.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)"
            )
            params.update(west=west, south=south, east=east, north=north)

        if prov:
            # case-insensitive, trimmed match
            where.append("TRIM(LOWER(b.provinsi)) = TRIM(LOWER(:provinsi))")
            params["provinsi"] = prov

        if kota:
            # case-insensitive, trimmed match for kota as well
            where.append("TRIM(LOWER(b.kota)) = TRIM(LOWER(:kota))")
            params["kota"] = kota

        sql = f"""
        SELECT json_build_object(
          'type', 'FeatureCollection',
          'features', COALESCE(json_agg(f), '[]'::json)
        ) AS geojson
        FROM (
          SELECT json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(b.geom)::json,
            'properties',
              (to_jsonb(b) - 'geom')
              || to_jsonb(d)
          ) AS f
          FROM bangunan b
          JOIN hasil_proses_directloss d USING(id_bangunan)
          WHERE {" AND ".join(where)}
        ) sub;
        """

        return db.session.execute(text(sql), params).scalar()

    @staticmethod
    def fetch_provinsi():
        sql = """
        SELECT DISTINCT b.provinsi
        FROM hasil_proses_directloss d
        JOIN bangunan b USING (id_bangunan)
        ORDER BY b.provinsi
        """
        rows = db.session.execute(text(sql)).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def fetch_kota(provinsi):
        sql = """
        SELECT DISTINCT b.kota
        FROM hasil_proses_directloss d
        JOIN bangunan b USING (id_bangunan)
        WHERE TRIM(LOWER(b.provinsi)) = TRIM(LOWER(:provinsi))
        ORDER BY b.kota
        """
        rows = db.session.execute(text(sql), {"provinsi": provinsi}).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def fetch_aal_geojson(provinsi=None):
        """
        Menghasilkan GeoJSON FeatureCollection dari tabel hasil_aal_provinsi
        yang di-join dengan geom dari tabel provinsi.
        Opsi filter: ?provinsi=NamaProvinsi
        """
        where_clauses = ["1=1"]
        params = {}

        if provinsi:
            where_clauses.append("TRIM(LOWER(hap.provinsi)) = TRIM(LOWER(:provinsi))")
            params["provinsi"] = provinsi

        sql = f"""
        SELECT json_build_object(
          'type',       'FeatureCollection',
          'features',   COALESCE(json_agg(f), '[]'::json)
        ) AS geojson
        FROM (
          SELECT json_build_object(
            'type',     'Feature',
            'geometry', ST_AsGeoJSON(p.geom)::json,
            'properties', to_jsonb(hap)
          ) AS f
          FROM hasil_aal_provinsi hap
          JOIN provinsi p
            ON TRIM(LOWER(p.provinsi)) = TRIM(LOWER(hap.provinsi))
          WHERE {" AND ".join(where_clauses)}
        ) sub;
        """
        return db.session.execute(text(sql), params).scalar()

    @staticmethod
    def fetch_aal_provinsi_list():
        """
        Ambil semua nama provinsi yang ada di tabel hasil_aal_provinsi.
        """
        sql = """
        SELECT provinsi
        FROM hasil_aal_provinsi
        ORDER BY provinsi
        """
        rows = db.session.execute(text(sql)).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def fetch_aal_data(provinsi):
        """
        Ambil satu baris dari hasil_aal_provinsi berdasarkan provinsi,
        tanpa memerlukan kecocokan geometry.
        """
        sql = """
        SELECT *
        FROM hasil_aal_provinsi
        WHERE TRIM(LOWER(provinsi)) = TRIM(LOWER(:provinsi))
        """
        row = db.session.execute(text(sql), {"provinsi": provinsi}).mappings().first()
        return dict(row) if row else None

    # === Streaming CSV tanpa filter: semua data ===
    @staticmethod
    def stream_directloss_csv():
        """
        Stream CSV seluruh tabel hasil_proses_directloss + bangunan.
        Returns: (cursor, copy_sql, params)
        """
        # SQL meng-export semua tanpa WHERE
        copy_sql = """
        COPY (
          SELECT
            b.id_bangunan,
            b.provinsi,
            b.kota,
            d.direct_loss,
            d.loss_pct,
            d.other_field
          FROM bangunan b
          JOIN hasil_proses_directloss d USING (id_bangunan)
        ) TO STDOUT WITH CSV HEADER
        """
        raw_conn = db.session.connection().connection
        cur = raw_conn.cursor()
        return cur, copy_sql, {}

    @staticmethod
    def stream_aal_csv():
        """
        Stream CSV seluruh tabel hasil_aal_provinsi.
        Returns: (cursor, copy_sql, params)
        """
        copy_sql = """
        COPY (
          SELECT *
          FROM hasil_aal_provinsi
          ORDER BY provinsi
        ) TO STDOUT WITH CSV HEADER
        """
        raw_conn = db.session.connection().connection
        cur = raw_conn.cursor()
        return cur, copy_sql, {}
