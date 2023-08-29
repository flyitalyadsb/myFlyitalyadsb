from wtforms import StringField, SubmitField, BooleanField, DateField, validators, SelectField, PasswordField, form
from wtforms.validators import DataRequired
from starlette_wtf import StarletteForm


class MenuForm(StarletteForm):
    Mappa = SubmitField('Mappa generale')
    Mappa_my = SubmitField('La mia mappa')
    Report = SubmitField('Report')
    Sito = SubmitField('Fly Italy Adsb')
    Grafici = SubmitField('Grafici')


class EditForm(StarletteForm):
    reg = StringField('Registrazione')
    model = StringField('Modello')
    civmil = BooleanField('Militare')
    operator = StringField('Operatore')
    submit = SubmitField('Modifica')


class ReportForm(StarletteForm):
    BInizio = BooleanField('Data Inizio')
    inizio = DateField('Data Inizio', format='%Y-%m-%d')
    BFine = BooleanField('Data Fine')
    fine = DateField('Data Fine', format='%Y-%m-%d')
    BIcao = BooleanField("ICAO")
    icao = StringField("ICAO")
    BRegistration = BooleanField("Registration")
    Registration = StringField("Registrazione")
    BModello = BooleanField("Modello")
    Modello = StringField("Modello")
    BICAOTypeCode = BooleanField("Codice ICAO Modello")
    ICAOTypeCode = StringField("Codice ICAO Modello")
    BOperator = BooleanField("Operatore")
    Operator = StringField("Operatore")
    BCivMil = BooleanField("Militare")
    CivMil = BooleanField("Militare")
    only_mine = BooleanField("Solo il mio ricevitore")
    submit = SubmitField("Cerca")

class SliderForm(StarletteForm):
    raggio = StringField('Distanza dalla mia antenna in km', [validators.Optional()])


class OnlyMine(StarletteForm):
    only_mine = SelectField('Mostra...', choices=("solo i miei dati", "quelli di tutti"))

class LoginForm(StarletteForm):
    uuid = PasswordField('Uuid', validators=[DataRequired()], render_kw={"placeholder": "Uuid", "class": "login-field"})
    submit = SubmitField('Entra!', render_kw={"class": "btn btn-primary btn-large btn-block"})