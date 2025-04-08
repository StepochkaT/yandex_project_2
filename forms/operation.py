import datetime
from flask_wtf import FlaskForm
from wtforms import FloatField, DateTimeField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired


class OperationForm(FlaskForm):
    date = DateTimeField("Дата", default=datetime.datetime.now, format='%Y-%m-%d %H:%M:%S')
    amount = FloatField("Сумма", validators=[DataRequired()])
    category = StringField("Категория", validators=[DataRequired()])
    type = SelectField("Тип операции", choices=[("income", "Доход"), ("expense", "Расход")], validators=[DataRequired()])
    description = StringField("Описание")
    submit = SubmitField("Добавить операцию")