from flask import render_template, session
from flask import Blueprint
from modules.blueprint.commonMy.commonMy import login_required

grafici_bp = Blueprint('grafici', __name__)


@login_required
@grafici_bp.route('/grafici')
def grafici():
        return render_template("grafici/index.html")




