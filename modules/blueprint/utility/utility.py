from flask import Blueprint, render_template, current_app, send_from_directory, send_file
import os

utility_bp = Blueprint('utility_bp', __name__, template_folder='templates',
                       static_folder='static')  # static_url_path='assets'



@utility_bp.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


@utility_bp.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@utility_bp.errorhandler(400)
def bad_request(e):
    return render_template("400.html"), 400


@utility_bp.route('/favicon/<icon>')
def favicon_general(icon):
    return send_from_directory(os.path.join(current_app.root_path, 'modules/blueprint/utility/templates/favicon'), icon)


@utility_bp.route('/favicon.ico')
def favicon():
    return send_file(os.path.join(current_app.root_path, 'modules/blueprint/utility/templates/favicon') + "/favicon.ico")

@utility_bp.route('/style.css')
def style():
    return send_file(os.path.join(current_app.root_path, 'static') + "/style.css")