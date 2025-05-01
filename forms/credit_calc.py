import datetime
from flask_wtf import FlaskForm
from wtforms import FloatField, DateTimeField, SelectField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired


class CreditCalculatorForm(FlaskForm):
    name = StringField("Имя кредита", default='Калькулятор ещё не готов', validators=[DataRequired()])
    date = DateTimeField("Дата выдачи", default=datetime.datetime.now, format='%Y-%m-%d %H:%M:%S')
    amount = FloatField("Сумма кредита/займа", default=10000, validators=[DataRequired()])
    percent = FloatField("Процентная ставка", default=5, validators=[DataRequired()])
    term = IntegerField("Срок кредита/займа", default=3, validators=[DataRequired()])
    type_term = SelectField("Тип вклада", choices=[("year", "Год"), ("month", "Месяц")],
                            validators=[DataRequired()])
    repayment = SelectField("Переодичность погашения",
                            choices=[("monthly", "Ежемесячно"), ("annually", "Ежегодно")], validators=[DataRequired()])
    submit = SubmitField("Рассчитать")
