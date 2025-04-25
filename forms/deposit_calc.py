import datetime
from flask_wtf import FlaskForm
from wtforms import FloatField, DateTimeField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired


class DepositCalculatorForm(FlaskForm):
    date = DateTimeField("Дата", default=datetime.datetime.now, format='%Y-%m-%d %H:%M:%S')
    amount = FloatField("Сумма", default=1000, validators=[DataRequired()])
    term = IntegerField("Срок вклада", default=1, validators=[DataRequired()])
    type_term = SelectField("Тип вклада", choices=[("year", "Год"), ("month", "Месяц")],
                            validators=[DataRequired()])
    percent = FloatField("Процентная ставка", default=5, validators=[DataRequired()])
    submit = SubmitField("Рассчитать")
