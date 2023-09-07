from starlette_wtf import StarletteForm
from wtforms import StringField, SubmitField, BooleanField, DateField, validators, SelectField, PasswordField
from wtforms.validators import DataRequired


class MenuForm(StarletteForm):
    map = SubmitField('Map')
    my_map = SubmitField('My Map')
    report = SubmitField('Report')
    site = SubmitField('Fly Italy Adsb')
    graphs = SubmitField('Graphs')


class EditForm(StarletteForm):
    reg = StringField('Registration')
    model = StringField('Model')
    civmil = BooleanField('Military')
    operator = StringField('Operator')
    submit = SubmitField('Edit')


class ReportForm(StarletteForm):
    b_start = BooleanField('Start Date')
    start = DateField('Start Date', format='%Y-%m-%d')
    b_end = BooleanField('End Date')
    end = DateField('End Date', format='%Y-%m-%d')
    b_icao = BooleanField("ICAO")
    icao = StringField("ICAO")
    b_registration = BooleanField("Registration")
    registration = StringField("Registration")
    b_model = BooleanField("Model")
    model = StringField("Model")
    b_icao_type_code = BooleanField("ICAO Model Code")
    icao_type_code = StringField("ICAO Model Code")
    b_operator = BooleanField("Operator")
    operator = StringField("Operator")
    b_civ_mil = BooleanField("Military")
    civ_mil = BooleanField("Military")
    only_mine = BooleanField("Only my receiver")
    submit = SubmitField("Search")


class SliderForm(StarletteForm):
    radius = StringField('Distance from my antenna', [validators.Optional()])


class OnlyMine(StarletteForm):
    only_mine = SelectField('Show...', choices=("only my data", "all data"))


class LoginForm(StarletteForm):
    uuid = PasswordField('Uuid', validators=[DataRequired()], render_kw={"placeholder": "Uuid", "class": "login-field"})
    submit = SubmitField('Entra!', render_kw={"class": "btn btn-primary btn-large btn-block"})
