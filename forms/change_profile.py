from flask_wtf import FlaskForm
from wtforms import SubmitField, PasswordField, StringField, EmailField
from wtforms.validators import DataRequired


class ProfileForm(FlaskForm):
    email = EmailField("Почта:", validators=[DataRequired()])
    name = StringField("Имя пользователя", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField('Применить')
