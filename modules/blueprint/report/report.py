import logging
from typing import List

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from common_py.common import query_updater, aircraft_cache
from common_py.commonLiveReport import pagination_func
from utility.forms import ReportForm, EditForm
from utility.model import Flight, Aircraft, SessionData, flights_receiver
from utility.model import Volo_rep
from common_py.common import flash, get_flashed_message

report_bp = APIRouter()
templates = Jinja2Templates(directory="modules/blueprint/report/templates")
report_bp.logger = logging.getLogger("REPORT")
templates.env.globals["get_flashed_messages"] = get_flashed_message


@report_bp.api_route("/report", methods=["GET", "POST"])
async def report(request: Request, page: int = None):
    pagination = False
    sliced_aircrafts = False
    session_db = request.state.session_db
    session: SessionData = request.state.session
    session.selected_page = 1
    form = await ReportForm.from_formdata(request)
    if page:
        session.selected_page = page
        past_report = query_updater.reports[session.report]
        sliced_aircrafts, pagination = await pagination_func(logger=report_bp.logger, page=page,
                                                             aircrafts_func=past_report,
                                                             live=False)
        return templates.TemplateResponse('report.html',
                                          {"request": request, "form": form, "voli": sliced_aircrafts,
                                           "buttons": pagination})
    if form.is_submitted():
        query = select(Flight).filter(Flight.aircraft_id == Aircraft.id).options(joinedload(Flight.aircraft))
        if form.BInizio.data:
            query = query.filter(Flight.start >= form.inizio.data)
        if form.BFine.data:
            query = query.filter(Flight.end <= form.fine.data)
        if form.BIcao.data:
            query = query.filter(Aircraft.icao.ilike(f"%{form.icao.data}%"))
        if form.BRegistration.data:
            query = query.filter(Aircraft.Registration.ilike(f"%{form.Registration.data}%"))
        if form.BModello.data:
            query = query.filter(Aircraft.Type.ilike(f"%{form.Modello.data}%"))
        if form.BICAOTypeCode.data:
            query = query.filter(Aircraft.ICAOTypeCode.ilike(f"%{form.ICAOTypeCode.data}%"))
        if form.BOperator.data:
            query = query.filter(Aircraft.Operator.ilike(f"%{form.Operator.data}%"))
        if form.BCivMil.data:
            if form.CivMil.data:
                query = query.filter(Aircraft.CivMil is True)
            else:
                query = query.filter((Aircraft.CivMil is None) | (Aircraft.CivMil is not False))
        if form.only_mine.data:
            query = query.join(flights_receiver).filter(flights_receiver.c.ricevitore_id == session.receiver.id)
        result = await session_db.execute(query)
        voli: List[Flight] = result.scalars().all()
        if not voli:
            flash(request, 'Nessun aereo trovato con questi filtri.')
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


@report_bp.api_route("/editor", methods=["GET", "POST"])
async def show_or_edit_aircraft(request: Request, icao: str = None):
    session_db = request.state.session_db
    form: EditForm = await EditForm.from_formdata(request)
    result = await session_db.execute(select(Aircraft).filter_by(icao=icao))
    aereo_db: Aircraft = result.scalar_one_or_none()
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
            flash(request, 'Aereo modificato con successo.')
        else:
            session_db.add(Aircraft(icao=icao.upper(), Registration=reg, Type=model, CivMil=civmil, Operator=operator))
            await session_db.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            flash(request, 'Aereo aggiunto con successo.')

    if aereo_db:
        aircraft = aereo_db.repr()
    else:
        aircraft = None
    return templates.TemplateResponse('editor.html',
                                      {"request": request, "aircraft": aircraft, "form": form, "icao": icao})
