import datetime
from flask_wtf import FlaskForm
from wtforms import FloatField, DateTimeField, SelectField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired


class DepositCalculatorForm(FlaskForm):
    name = StringField("Имя вклада", default="Вклад 1", validators=[DataRequired()])
    date = DateTimeField("Дата открытия", default=datetime.datetime.now, format='%Y-%m-%d')
    amount = FloatField("Сумма", default=0, validators=[DataRequired()])
    term = IntegerField("Срок вклада", default=1, validators=[DataRequired()])
    type_term = SelectField("Тип вклада", choices=[("year", "Год"), ("month", "Месяц")],
                            validators=[DataRequired()])
    percent = FloatField("Процентная ставка", default=5, validators=[DataRequired()])
    submit = SubmitField("Рассчитать")
