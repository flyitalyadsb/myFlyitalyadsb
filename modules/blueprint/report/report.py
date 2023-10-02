import logging
from typing import List

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from common_py.common import query_updater, aircraft_cache
from common_py.commonLiveReport import pagination_func
from utility.forms import ReportForm, EditForm
from utility.model import Flight, Aircraft, SessionData, flights_receiver, Receiver
from utility.model import FlightRep
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
        sliced_aircrafts, pagination = await pagination_func(session_db, logger=report_bp.logger, page=page,
                                                             aircrafts_func=past_report,
                                                             live=False)
        return templates.TemplateResponse('report.html',
                                          {"request": request, "form": form, "flights": sliced_aircrafts,
                                           "buttons": pagination})
    if form.is_submitted():
        query = select(Flight).filter(Flight.aircraft_id == Aircraft.id).options(joinedload(Flight.aircraft))
        if form.b_start.data:
            query = query.filter(Flight.start >= form.start.data)
        if form.b_end.data:
            query = query.filter(Flight.end <= form.end.data)
        if form.b_icao.data:
            query = query.filter(Aircraft.icao.ilike(f"%{form.icao.data}%"))
        if form.b_registration.data:
            query = query.filter(Aircraft.registration.ilike(f"%{form.registration.data}%"))
        if form.b_model.data:
            query = query.filter(Aircraft.type.ilike(f"%{form.model.data}%"))
        if form.b_icao_type_code.data:
            query = query.filter(Aircraft.icao_type_code.ilike(f"%{form.icao_type_code.data}%"))
        if form.b_operator.data:
            query = query.filter(Aircraft.operator.ilike(f"%{form.operator.data}%"))
        if form.b_civ_mil.data:
            if form.civ_mil.data:
                query = query.filter(Aircraft.civ_mil is True)
            else:
                query = query.filter((Aircraft.civ_mil is None) | (Aircraft.civ_mil is not False))
        if form.only_mine.data:
            query = query.join(flights_receiver).filter(flights_receiver.c.receiver_id == session.receiver.id)
        result = await session_db.execute(query)
        flights: List[Flight] = result.scalars().all()
        if not flights:
            flash(request, 'No aircraft found with these filters.')
            return templates.TemplateResponse('report.html',
                                              {"request": request, "form": form})
        flights_list = []
        for flight in flights:
            flights_list.append(FlightRep(flight).to_dict())
        query_updater.reports.append(flights_list)
        session.report = query_updater.reports.index(flights_list)
        sliced_aircrafts, pagination = await pagination_func(session_db, logger=report_bp.logger, page=1, aircrafts_func=flights_list,
                                                             live=False)
    return templates.TemplateResponse('report.html',
                                      {"request": request, "form": form, "flights": sliced_aircrafts,
                                       "buttons": pagination})


@report_bp.api_route("/editor", methods=["GET", "POST"])
async def show_or_edit_aircraft(request: Request, icao: str = None):
    receiver: Receiver = request.state.session.receiver
    if receiver.editor:
        session_db = request.state.session_db
        form: EditForm = await EditForm.from_formdata(request)
        result = await session_db.execute(select(Aircraft).filter_by(icao=icao))
        aircraft_db: Aircraft = result.scalar_one_or_none()
        if await form.validate_on_submit():
            reg = form.reg.data
            model = form.model.data
            civmil = form.civmil.data
            operator = form.operator.data
            if aircraft_db:
                aircraft_db.registration = reg if reg else aircraft_db.registration
                aircraft_db.type = model if model else aircraft_db.type
                aircraft_db.civ_mil = civmil if civmil is not None else aircraft_db.civ_mil
                aircraft_db.operator = operator if operator else aircraft_db.operator
                await session_db.commit()
                if icao.lower() in aircraft_cache:
                    aircraft_cache.pop(icao.lower())
                flash(request, 'Aircraft successfully modified.')
            else:
                session_db.add(
                    Aircraft(icao=icao.upper(), registration=reg, type=model, civ_mil=civmil, operator=operator))
                await session_db.commit()
                if icao.lower() in aircraft_cache:
                    aircraft_cache.pop(icao.lower())
                flash(request, 'Aircraft successfully added')

        if aircraft_db:
            aircraft = aircraft_db.repr()
        else:
            aircraft = None
        return templates.TemplateResponse('editor.html',
                                          {"request": request, "aircraft": aircraft, "form": form, "icao": icao})
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
