import logging
import time
from typing import List

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from common_py.common import query_updater, aircraft_cache
from common_py.commonLiveReport import pagination_func
from utility.forms import ReportForm, EditForm
from utility.model import Volo, Aereo
from utility.model import Volo_rep

report_bp = APIRouter()
templates = Jinja2Templates(directory="modules/blueprint/report/templates")
report_bp.logger = logging.getLogger("REPORT")


@report_bp.api_route("/report", methods=["GET", "POST"])
async def report(request: Request):
    pagination = False
    sliced_aircrafts = False
    session_db = request.state.session_db
    session = request.state.session
    session.selected_page = 1
    form = await ReportForm.from_formdata(request)
    if form.is_submitted():
        query = select(Volo).filter(Volo.aereo_id == Aereo.id).options(joinedload(Volo.aereo))
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
            query = query.filter(Aereo.ICAOTypeCode == form.ICAOTypeCode.data.upper())
        if form.BOperator.data:
            query = query.filter(Aereo.Operator == form.Operator.data)
        if form.BCivMil.data:
            if form.CivMil.data:
                query = query.filter(Aereo.CivMil == True)
            else:
                query = query.filter((Aereo.CivMil == None) | (Aereo.CivMil == False))
        if form.only_mine.data:
            query = query.filter(session.ricevitore in Volo.ricevitori)
        result = await session_db.execute(query)
        voli: List[Volo] = result.scalars().all()
        if not voli:
            # flash('Nessun aereo trovato con questi filtri.', 'warning')
            print("Nessun aereo trovato con questi filtri.")
            return templates.TemplateResponse('report.html',
                                              {"request": request, "form": form})
        voli_list = []
        for volo in voli:
            voli_list.append(Volo_rep(volo).to_dict())
        query_updater.reports.append(voli_list)
        session.report = query_updater.reports.index(voli_list)
        sliced_aircrafts, pagination = await pagination_func(logger=report_bp.logger, page=1, aircrafts_func=voli_list,
                                                             live=False)
    return templates.TemplateResponse('report.html',
                                      {"request": request, "form": form, "voli": sliced_aircrafts,
                                       "buttons": pagination})


@report_bp.get("/report_table")
async def report_table_pagination_func(request: Request, page: int):
    session = request.state.session
    if session.report:
        voli = query_updater.reports[session.report]
        sliced_aircrafts, pagination = await pagination_func(report_bp.logger, page, voli, False)
        return templates.TemplateResponse('report_table.html',
                                          {"request": request, "voli_dict": sliced_aircrafts, "pagination": pagination})
    else:
        return "None"


"""
                {% with message = get_flashed_messages() %}
                    {% if message %}
                        <div class="success alert-success alert-dismissible show" role="alert">
                            {{ message[0] }}
                        </div>
                    {% endif %}
                {% endwith %}
                """


@report_bp.api_route("/editor", methods=["GET", "POST"])
async def show_or_edit_aircraft(request: Request, icao: str = None):
    session_db = request.state.session_db
    form: EditForm = await EditForm.from_formdata(request)
    result = await session_db.execute(select(Aereo).filter_by(icao=icao))
    aereo_db: Aereo = result.scalar_one_or_none()
    if await form.validate_on_submit():
        reg = form.reg.data
        model = form.model.data
        civmil = form.civmil.data
        operator = form.operator.data
        if aereo_db:
            aereo_db.Registration = reg if reg else aereo_db.Registration
            aereo_db.Type = model if model else aereo_db.Type
            aereo_db.CivMil = civmil if not None else aereo_db.CivMil
            aereo_db.Operator = operator if operator else aereo_db.Operator
            await session_db.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            # flash('Aereo modificato con successo.', 'success')
        else:
            session_db.add(Aereo(icao=icao.upper(), Registration=reg, Type=model, CivMil=civmil, Operator=operator))
            await session_db.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            # flash('Aereo aggiunto con successo.', 'success')

    if aereo_db:
        aircraft = aereo_db.repr()
    else:
        aircraft = None
    return templates.TemplateResponse('editor.html',
                                      {"request": request, "aircraft": aircraft, "form": form, "icao": icao})
