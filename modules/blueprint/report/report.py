from flask import Blueprint, render_template, session, request, flash
from utility.model import Volo, Aereo
from utility.forms import ReportForm, EditForm
import time
import logging
import datetime
from utility.model import db, Volo_rep
from common_py.commonLiveReport import pagination_func
from common_py.common import query_updater, aircraft_cache
from modules.blueprint.commonMy.commonMy import login_required
from typing import List

report_bp = Blueprint('report_bp', __name__, template_folder='templates',
                      static_folder='static')
report_bp.logger = logging.getLogger("REPORT")



@report_bp.route("/report", methods=["GET", "POST"])
@login_required
async def report():
    session["selected_page"] = 1
    form = ReportForm()

    if form.is_submitted():
        query = Volo.query.join(Aereo)
        if form.BInizio.data:
            query = query.filter(Volo.inizio >= int(time.mktime(form.inizio.data.timetuple())))
        if form.BFine.data:
            query = query.filter(
                Volo.fine <= int(time.mktime(form.fine.data.timetuple())))  # da datetime.date a timestamp
        if form.BIcao.data:
            query = query.filter(Aereo.icao == form.icao.data)
        if form.BRegistration.data:
            query = query.filter(Aereo.Registration == form.Registration.data)
        if form.BModello.data:
            query = query.filter(Aereo.Type == form.Modello.data)
        if form.BICAOTypeCode.data:
            query = query.filter(form.ICAOTypeCode.data.upper() == Aereo.ICAOTypeCode)
        if form.BOperator.data:
            query = query.filter(Aereo.Operator == form.Operator.data)
        if form.BCivMil.data:
            if form.CivMil.data:
                query = query.filter(Aereo.CivMil == True)
            else:
                form.CivMil.data = query.filter((Aereo.CivMil == None) | (Aereo.CivMil == False))
        if form.only_mine.data:
            query = query.filter(session["ricevitore"] in Volo.ricevitori)
        voli: List[Volo] = query.all()
        if not voli:
            flash('Nessun aereo trovato con questi filtri.', 'warning')
            return render_template("report.html", form=form)
        for volo in voli:
            volo.inizio = datetime.datetime.fromtimestamp(float(volo.inizio))
            volo.fine = datetime.datetime.fromtimestamp(float(volo.fine))
        voli_list = []
        for volo in voli:
            voli_list.append(Volo_rep(volo).to_dict())
        query_updater.reports.append(voli_list)
        session["report"] = query_updater.reports.index(voli_list)
        sliced_aircrafts, pagination = await pagination_func(logger=report_bp.logger, page=1, aircrafts=voli_list,
                                                             live=False)
        return render_template("report.html", form=form, voli=sliced_aircrafts, pagination=pagination)
    return render_template("report.html", form=form)



@report_bp.route("/report_table")
@login_required
async def report_table_pagination_func():
    if "report" in session.keys():
        page = request.args.get("page", type=int)
        voli = query_updater.reports[session["report"]]
        sliced_aircrafts, pagination = await pagination_func(report_bp.logger, page, voli, False)
        return render_template("report_table.html", voli_dict=sliced_aircrafts, pagination=pagination)
    else:
        return "None"



@report_bp.route("/editor", methods=["GET", "POST"])
@login_required
async def show_or_edit_aircraft():
    form = EditForm()
    icao = request.args.get('icao')
    aereo_db: Aereo = Aereo.query.filter_by(icao=icao.upper()).first()
    if form.validate_on_submit():
        reg = form.reg.data
        model = form.model.data
        civmil = form.civmil.data
        operator = form.operator.data
        if aereo_db:
            aereo_db.Registration = reg
            aereo_db.Type = model
            aereo_db.CivMil = civmil
            aereo_db.Operator = operator
            db.session.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            flash('Aereo modificato con successo.', 'success')
        else:
            db.session.add(Aereo(icao=icao.upper(), Registration=reg, Type=model, CivMil=civmil, Operator=operator))
            db.session.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            flash('Aereo aggiunto con successo.', 'success')

    if aereo_db:
        aircraft = aereo_db.repr()
    else:
        aircraft = None
    return render_template("editor.html", aircraft=aircraft, form=form, icao=icao)
