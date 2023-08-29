from utility.model import Volo, Aereo
from utility.forms import ReportForm, EditForm
import time
import logging
import datetime
from utility.model import Volo_rep, SessionData
from common_py.commonLiveReport import pagination_func
from common_py.common import query_updater, aircraft_cache
from typing import List
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


report_bp = APIRouter()
templates = Jinja2Templates(directory="./templates")
report_bp.logger = logging.getLogger("REPORT")



@report_bp.get("/report")
@report_bp.post("/report")
async def report(request: Request):
    request.session_data.selected_page = 1
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
            query = query.filter(request.session_data.ricevitore in Volo.ricevitori)
        voli: List[Volo] = query.all()
        if not voli:
            flash('Nessun aereo trovato con questi filtri.', 'warning')
            return templates.TemplateResponse('report.html',
                                              {"request": request, "form": form})
        for volo in voli:
            volo.inizio = datetime.datetime.fromtimestamp(float(volo.inizio))
            volo.fine = datetime.datetime.fromtimestamp(float(volo.fine))
        voli_list = []
        for volo in voli:
            voli_list.append(Volo_rep(volo).to_dict())
        query_updater.reports.append(voli_list)
        request.session_data.report = query_updater.reports.index(voli_list)
        sliced_aircrafts, pagination = await pagination_func(logger=report_bp.logger, page=1, aircrafts=voli_list,
                                                             live=False)
        return templates.TemplateResponse('report.html',
                                          {"request": request, "form": form, "voli":sliced_aircrafts, "pagination":pagination})



@report_bp.get("/report_table")
async def report_table_pagination_func(request: Request, page: int):
    if request.session_data.report:
        voli = query_updater.reports[request.session_data.report]
        sliced_aircrafts, pagination = await pagination_func(report_bp.logger, page, voli, False)
        return templates.TemplateResponse('report_table.html',{"request": request, "voli_dict": sliced_aircrafts, "pagination":pagination})
    else:
        return "None"



@report_bp.get("/editor")
@report_bp.post("/editor")
async def show_or_edit_aircraft(request: Request):
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
            await SessionData.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            flash('Aereo modificato con successo.', 'success')
        else:
            await SessionData.add(Aereo(icao=icao.upper(), Registration=reg, Type=model, CivMil=civmil, Operator=operator))
            await SessionData.commit()
            if icao.lower() in aircraft_cache:
                aircraft_cache.pop(icao.lower())
            flash('Aereo aggiunto con successo.', 'success')

    if aereo_db:
        aircraft = aereo_db.repr()
    else:
        aircraft = None
    return templates.TemplateResponse('editor.html', {"request": request, "aircraft": aircraft, "form":form, "icao":icao})
