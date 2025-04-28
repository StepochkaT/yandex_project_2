from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import math

from flask import Flask, render_template, redirect, request, abort, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_apscheduler import APScheduler
from currency_updater import update_currency_data, load_data

from data.category import Category
from forms.cat_form import CategoryForm
from forms.period import PeriodForm
from forms.user import RegisterForm, LoginForm
from forms.operation import OperationForm
from forms.deposit_calc import DepositCalculatorForm
from forms.credit_calc import CreditCalculatorForm
from data.users import User
from data.operations import Operation
from data import db_session

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'super_secret_key'


class Config:
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

scheduler.add_job(
    id='update_currency_data',
    func=update_currency_data,
    trigger='interval',
    hours=2
)


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

    db_sess = db_session.create_session()
    categories = db_sess.query(Category).filter(
        (Category.user_id == None) | (Category.user_id == current_user.id)
    ).all()

    form.category.choices = [(cat.id, cat.name) for cat in categories]

    if form.validate_on_submit():
        operation = Operation(
            date=form.date.data,
            amount=form.amount.data,
            category_id=form.category.data,
            type=form.type.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db_sess.add(operation)
        db_sess.commit()
        return redirect('/')
    return render_template('add_operation.html', form=form)


@app.route("/operations", methods=["GET", "POST"])
@login_required
def operations():
    form = PeriodForm()
    page = int(request.args.get("page", 1))
    per_page = 10

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today
    selected_type = 'all'
    selected_category = 'all'
    show_all = False
    search_query = ''

    user_operations = current_user.operations
    db_sess = db_session.create_session()

    user_categories = [{
        'id': c.id,
        'name': c.name,
        'type': c.type
    } for c in current_user.categories]

    base_categories = [{
        'id': c.id,
        'name': c.name,
        'type': c.type
    } for c in db_sess.query(Category).filter(Category.user_id == None)]

    all_categories = [{'id': 'all', 'name': 'Все', 'type': 'all'}]
    all_categories.extend(base_categories + user_categories)

    form.category.choices = [(str(c['id']), c['name']) for c in all_categories]

    if request.method == "POST":
        date_range_str = form.date_range.data
        selected_type = form.operation_type.data
        selected_category = form.category.data
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
        selected_category = request.args.get("selected_category", "all")
        form.date_range.data = ' to '.join([f"{start_date}", f"{end_date}"])
        form.operation_type.data = selected_type
        form.category.data = selected_category

    operations_in_period = user_operations

    if not show_all:
        operations_in_period = filter(
            lambda op: start_date <= op.date.date() <= end_date,
            operations_in_period
        )

    if selected_type != 'all':
        operations_in_period = filter(lambda op: op.type == selected_type, operations_in_period)

    if selected_category != 'all':
        operations_in_period = filter(lambda op: str(op.category_id) == selected_category, operations_in_period)

    if search_query:
        operations_in_period = filter(lambda op: search_query.lower() in op.description.lower(), operations_in_period)

    operations_in_period = list(operations_in_period)
    operations_in_period.sort(key=lambda op: op.date, reverse=True)

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
        selected_category=selected_category,
        show_all=show_all,
        search_query=search_query,
        categories=all_categories
    )


@app.route('/edit_operation/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_operation(id):
    form = OperationForm()
    db_sess = db_session.create_session()
    operation = db_sess.query(Operation).filter(Operation.id == id, Operation.user_id == current_user.id).first()

    if not operation:
        abort(404)

    categories = db_sess.query(Category).filter(
        ((Category.user_id == None) | (Category.user_id == current_user.id)) &
        (Category.type == operation.type)
    ).all()
    form.category.choices = [(str(c.id), c.name) for c in categories]

    if request.method == "GET":
        form.date.data = operation.date
        form.amount.data = operation.amount
        form.category.data = str(operation.category_id)
        form.type.data = operation.type
        form.description.data = operation.description

    if form.validate_on_submit():
        operation.date = form.date.data
        operation.amount = form.amount.data
        operation.category_id = int(form.category.data)
        operation.type = form.type.data
        operation.description = form.description.data

        db_sess.commit()
        return redirect('/operations')

    return render_template('add_operation.html', title='Редактирование операции', form=form)


@app.route("/operations/delete/<int:id>", methods=["POST"])
@login_required
def delete_operation(id):
    db_sess = db_session.create_session()
    operation = db_sess.query(Operation).filter(Operation.id == id, Operation.user_id == current_user.id).first()
    if operation:
        db_sess.delete(operation)
        db_sess.commit()

    query_params = {
        "page": request.args.get("page", 1),
        "operation_type": request.args.get("operation_type", "all"),
        "show_all": request.args.get("show_all", ""),
        "search_query": request.args.get("search_query", "")
    }
    query_str = "&".join([f"{k}={v}" for k, v in query_params.items() if v])
    return redirect(f"/operations?{query_str}")


@app.route('/get_categories/<op_type>')
@login_required
def get_categories(op_type):
    db_sess = db_session.create_session()
    categories = db_sess.query(Category).filter(
        ((Category.user_id == None) | (Category.user_id == current_user.id)) &
        (Category.type == op_type)
    ).all()
    return jsonify([(cat.id, cat.name) for cat in categories])


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    form = CategoryForm()
    db_sess = db_session.create_session()

    if form.validate_on_submit():
        new_category = Category(
            name=form.name.data,
            type=form.type.data,
            user_id=current_user.id
        )
        db_sess.add(new_category)
        db_sess.commit()

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    show_my = request.args.get('show_my', '0') == '1'

    query = db_sess.query(Category)
    if search_query:
        query = query.filter(Category.name.ilike(f"%{search_query}%"))

    if show_my:
        query = query.filter(Category.user_id == current_user.id)
        categories_list = query.order_by(Category.name).all()
        base_categories = []
        user_categories = categories_list
    else:
        categories_list = query.order_by(Category.name).all()
        base_categories = [c for c in categories_list if c.user_id is None]
        user_categories = [c for c in categories_list if c.user_id == current_user.id]

    per_page = 10
    total_pages = math.ceil(len(user_categories) / per_page)
    user_categories = user_categories[(page - 1) * per_page: page * per_page]

    return render_template(
        "category_manager.html",
        base_categories=base_categories,
        user_categories=user_categories,
        current_page=page,
        total_pages=total_pages,
        search_query=search_query,
        show_my=show_my,
        form=form,
        title='Категории'
    )


@app.route('/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    db_sess = db_session.create_session()
    category = db_sess.query(Category).filter(Category.id == id).first()

    if not category:
        abort(404)

    if category.user_id is None:
        return redirect('/categories')

    if category.user_id != current_user.id:
        abort(403)

    db_sess.query(Operation).filter(
        Operation.category_id == category.id,
        Operation.user_id == current_user.id
    ).delete(synchronize_session=False)

    db_sess.delete(category)
    db_sess.commit()

    page = request.form.get("page", "1")
    search_query = request.form.get("search_query", "")
    return redirect(f"/categories?page={page}&search={search_query}")


@app.route("/currency")
def currency_page():
    currencies = {"USD": 'Американский доллар', "EUR": 'Евро', "CNY": 'Китайский юань', "RUB": 'Российский рубль'}
    return render_template("currency_test.html", currencies=currencies, title='Конвертер валют')


@app.route("/calculators")
def calculators_page():
    return render_template("calculators.html", title='Калькуляторы')


@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def calculate_deposit():
    form = DepositCalculatorForm()
    if form.validate_on_submit():
        list_of_charges = []
        name = request.form["name"]
        date_open = request.form["date"]
        date = datetime(int(date_open[:4]), int(date_open[5:7]), int(date_open[8:]))
        amount = request.form["amount"]
        percent = request.form["percent"]
        term = request.form["term"]
        type_term = request.form["type_term"]
        if type_term == 'year':
            term = int(term) * 12
        result = int(int(amount) * (1 + ((int(percent) / 100) / 12)) ** int(term))
        income = result - int(amount)
        for _ in range(int(term)):
            charge = round((int(amount) * (1 + ((int(percent) / 100) / 12)) ** 1) - int(amount), 2)
            amount = (int(amount) * (1 + ((int(percent) / 100) / 12)) ** 1)
            date = date + relativedelta(months=1)
            list_of_charges.append([str(date)[:10], str(charge)])
        return render_template('deposit_calculator.html', form=form, income=income,
                               amount_received=result, title="Депозитный калькулятор", list_of_charges=list_of_charges)
    return render_template('deposit_calculator.html', form=form, title="Депозитный калькулятор",
                           income=0, amount_received=0)


@app.route("/credit", methods=['GET', 'POST'])
@login_required
def credit_page():
    form = CreditCalculatorForm()
    if form.validate_on_submit():
        name = request.form["name"]
        amount = request.form["amount"]
        percent = request.form["percent"]
        term = int(request.form["term"])
        type_term = request.form["type_term"]
        repayment = request.form["repayment"]
        p = (1 / 12) * int(percent)
        if type_term == "year":
            term = int(term) * 12
        monthly_payment = int(amount) * (p + (p / (((1 + p) ** term) - 1)))
        income = monthly_payment * term - int(amount)
        result = income + int(amount)
        return render_template('credit_calculator.html', form=form, income=income,
                               amount_received=result, title="Кредитный калькулятор")
    return render_template('credit_calculator.html', form=form, title="Кредитный калькулятор")


@app.route('/savings', methods=['POST', 'GET'])
def saving_cal_page():
    if request.method == "GET":
        return render_template("savings_calculator.html", title='Калькулятор сохранений')
    elif request.method == 'POST':
        if (not request.form['goal_cost'].isdigit()) or (not request.form['contribution'].isdigit()) or (
                not request.form['gap'].isdigit()):
            abort(401)
        else:
            quantity = int(request.form['goal_cost']) / (int(request.form['contribution']) * (int(request.form['gap'])))
            result = (f'Вы соберёте на цель «{request.form["name_goal"]}» через'
                      f' {int(quantity) * (int(request.form["gap"]))} дня.')
            return render_template("savings_calculator.html", title='Калькулятор сохранений', result=result)


@app.route("/currency/data", methods=["POST"])
def currency_data():
    data = load_data()
    from_curr = request.json.get("from_currency")
    to_curr = request.json.get("to_currency")
    amount = float(request.json.get("amount", 1))

    if from_curr not in data or to_curr not in data:
        return jsonify({"error": "Некорректные данные"}), 400

    common_times = sorted(set(data[from_curr]) & set(data[to_curr]))
    times = [datetime.fromisoformat(t).isoformat() for t in common_times]
    rates = [data[from_curr][t] / data[to_curr][t] for t in common_times]
    converted = amount * rates[-1] if rates else 0

    return jsonify({
        "converted": round(converted, 4),
        "graph": {
            "x": times,
            "y": rates,
            "from": from_curr,
            "to": to_curr
        }
    })


if __name__ == '__main__':
    main()
