from datetime import datetime, date
import math

from flask import Flask, render_template, redirect, request, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from forms.period import PeriodForm
from forms.user import RegisterForm, LoginForm
from forms.operation import OperationForm
from data.users import User
from data.operations import Operation
from data import db_session

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'super_secret_key'


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def main():
    db_session.global_init("db/database2.db")
    app.run()


@app.route("/")
def index():
    if current_user.is_authenticated:
        now = datetime.now()
        current_month = now.strftime("%B %Y")

        operations_this_month = list(filter(
            lambda op: op.date.month == now.month and op.date.year == now.year,
            current_user.operations
        ))

        income = sum(op.amount for op in operations_this_month if op.type == "income")
        expense = sum(op.amount for op in operations_this_month if op.type == "expense")
        balance = income - expense

        return render_template(
            "dashboard.html",
            authenticated=True,
            income=income,
            expense=expense,
            balance=balance,
            current_month=current_month
        )
    else:
        return render_template("dashboard.html", authenticated=False)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            username=form.username.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        print('smth')
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/add_operation', methods=['GET', 'POST'])
@login_required
def add_operation():
    form = OperationForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        operation = Operation(
            date=form.date.data,
            amount=form.amount.data,
            category=form.category.data,
            type=form.type.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db_sess.commit()

        db_sess = db_session.create_session()
        user = db_sess.query(User).get(current_user.id)
        user.operations.append(operation)
        db_sess.commit()
        return redirect('/')
    return render_template('add_operation.html', form=form)


@app.route("/operations", methods=["GET", "POST"])
@login_required
def operations():
    form = PeriodForm()
    page = int(request.args.get("page", 1))
    per_page = 1

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today
    selected_type = 'all'
    show_all = False
    search_query = ''

    if request.method == "POST":
        date_range_str = form.date_range.data
        selected_type = form.operation_type.data
        show_all = 'show_all' in request.form
        search_query = request.form.get('search_query', '')

        if not show_all and date_range_str:
            try:
                start_str, end_str = date_range_str.split(" to ")
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            except ValueError:
                return redirect("/operations")
    else:
        form.date_range.data = ' to '.join([f"{start_date}", f"{end_date}"])
        form.operation_type.data = selected_type

    # фильтрация
    operations_in_period = current_user.operations
    if not show_all:
        operations_in_period = filter(
            lambda op: start_date <= op.date.date() <= end_date,
            operations_in_period
        )

    if selected_type != 'all':
        operations_in_period = filter(lambda op: op.type == selected_type, operations_in_period)

    if search_query:
        operations_in_period = filter(lambda op: search_query.lower() in op.description.lower(), operations_in_period)

    operations_in_period = list(operations_in_period)

    total_pages = math.ceil(len(operations_in_period) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    current_ops = operations_in_period[start:end]

    return render_template(
        "operations.html",
        form=form,
        operations=current_ops,
        total_pages=total_pages,
        current_page=page,
        selected_type=selected_type,
        show_all=show_all,
        search_query=search_query
    )


@app.route('/edit_operation/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_operation(id):
    form = OperationForm()
    db_sess = db_session.create_session()
    operation = db_sess.query(Operation).filter(Operation.id == id, Operation.user_id == current_user.id).first()

    if not operation:
        abort(404)

    if request.method == "GET":
        form.date.data = operation.date
        form.amount.data = operation.amount
        form.category.data = operation.category
        form.type.data = operation.type
        form.description.data = operation.description

    if form.validate_on_submit():
        operation.date = form.date.data
        operation.amount = form.amount.data
        operation.category = form.category.data
        operation.type = form.type.data
        operation.description = form.description.data

        db_sess.commit()
        return redirect('/operations')

    return render_template('add_operation.html', title='Редактирование операции', form=form)


if __name__ == '__main__':
    main()
