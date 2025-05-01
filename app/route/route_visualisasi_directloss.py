# app/route/route_visualisasi_directloss.py

from flask import Blueprint, request, jsonify
from app.service.service_visualisasi_directloss import GedungService
import math

gedung_bp = Blueprint('gedung', __name__, url_prefix='/api')

@gedung_bp.route('/gedung', methods=['GET'])
def get_gedung():
    """
    GET /api/gedung
      Query params (optional):
        - bbox=minx,miny,maxx,maxy
        - provinsi=<nama provinsi>
        - kota=<nama kota>
    Returns a GeoJSON FeatureCollection.
    """
    bbox    = request.args.get('bbox')
    prov    = request.args.get('provinsi')
    kota    = request.args.get('kota')
    geojson = GedungService.get_geojson(bbox=bbox, prov=prov, kota=kota)
    return jsonify(geojson)

@gedung_bp.route('/provinsi', methods=['GET'])
def list_provinsi():
    """
    GET /api/provinsi
    Returns JSON array of all distinct provinsi.
    """
    data = GedungService.get_provinsi_list()
    return jsonify(data)

@gedung_bp.route('/kota', methods=['GET'])
def list_kota():
    """
    GET /api/kota?provinsi=<nama provinsi>
    Returns JSON array of all distinct kota in the given provinsi.
    """
    prov = request.args.get('provinsi')
    if not prov:
        return jsonify([]), 400
    data = GedungService.get_kota_list(prov)
    return jsonify(data)

@gedung_bp.route('/aal-provinsi', methods=['GET'])
def get_aal_geojson():
    """
    GET /api/aal-provinsi
      Query params (optional):
        - provinsi=<nama provinsi>
    Returns GeoJSON FeatureCollection dari AAL per provinsi.
    """
    prov = request.args.get('provinsi')
    geojson = GedungService.get_aal_geojson(prov)
    return jsonify(geojson)

@gedung_bp.route('/aal-provinsi-list', methods=['GET'])
def list_aal_provinsi():
    """
    GET /api/aal-provinsi-list
    Mengembalikan JSON array nama-nama provinsi dari hasil_aal_provinsi.
    """
    data = GedungService.get_aal_provinsi_list()
    return jsonify(data)

@gedung_bp.route('/aal-provinsi-data', methods=['GET'])
def aal_data():
    """
    GET /api/aal-provinsi-data?provinsi=...
    Returns JSON object of all AAL fields (sanitized) for the given provinsi.
    """
    prov = request.args.get('provinsi')
    if not prov:
        return jsonify({"error": "provinsi required"}), 400

    data = GedungService.get_aal_data(prov)
    if not data:
        return jsonify({}), 404

    # sanitize NaN or infinite values
    for key, value in data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            data[key] = 0.0

    return jsonify(data)


def setup_visualisasi_routes(app):
    """
    Register this blueprint on the Flask application.
    Call this in create_app() after other blueprint registrations.
    """
    app.register_blueprint(gedung_bp)
