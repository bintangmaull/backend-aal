from flask import Blueprint
from app.controller.controller_crud_hsbgn import HSBGNController

# Buat Blueprint untuk API HSBGN
hsbgn_bp = Blueprint("hsbgn_bp", __name__, url_prefix="/api/hsbgn")

# Endpoint untuk CRUD HSBGN dengan id_kota sebagai string
hsbgn_bp.add_url_rule("",               view_func=HSBGNController.get_all,       methods=["GET"])
hsbgn_bp.add_url_rule("/<string:hsbgn_id>", view_func=HSBGNController.get_by_id,    methods=["GET"])
hsbgn_bp.add_url_rule("/kota/<string:kota>", view_func=HSBGNController.get_by_kota, methods=["GET"])
hsbgn_bp.add_url_rule("",               view_func=HSBGNController.create,        methods=["POST"])
hsbgn_bp.add_url_rule("/<string:hsbgn_id>", view_func=HSBGNController.update,      methods=["PUT"])
hsbgn_bp.add_url_rule("/<string:hsbgn_id>", view_func=HSBGNController.delete,      methods=["DELETE"])
