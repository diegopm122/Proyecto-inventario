from flask import Flask, render_template, redirect, request
from models import db, User, Item, Solicitud
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# 🔐 HASH
from flask_bcrypt import Bcrypt

# 📧 MAIL
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SECRET_KEY'] = 'secreto'

# 📧 CONFIGURACIÓN MAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'microgeo30@gmail.com'
app.config['MAIL_PASSWORD'] = 'ihvi xomc iowx rnho'
app.config['MAIL_DEFAULT_SENDER'] = ('Inventario Microgeo', 'microgeo30@gmail.com')

db.init_app(app)

bcrypt = Bcrypt(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = '/'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 🔐 LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter(
            (User.username == user_input) | (User.email == user_input)
        ).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect('/dashboard')

    return render_template('login.html')


# 🆕 REGISTRO
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not email.endswith('@microgeo.cl'):
            return "Solo correos @microgeo.cl permitidos"

        existe = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existe:
            return "Usuario o correo ya existe"

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        nuevo = User(
            username=username,
            email=email,
            password=hashed_password,
            role='usuario'
        )

        db.session.add(nuevo)
        db.session.commit()

        return redirect('/')

    return render_template('registro.html')


# 🏠 DASHBOARD
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# 📦 INVENTARIO
@app.route('/inventario')
@login_required
def inventario():
    items = Item.query.all()
    return render_template('inventario.html', items=items)


# ➕ AGREGAR PRODUCTO
@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    if current_user.role != 'admin':
        return "No autorizado"

    nombre = request.form.get('nombre')
    cantidad = request.form.get('cantidad')

    nuevo = Item(nombre=nombre, cantidad=int(cantidad))

    db.session.add(nuevo)
    db.session.commit()

    return redirect('/inventario')


# 📄 SOLICITAR PRODUCTO + EMAIL
@app.route('/solicitar', methods=['POST'])
@login_required
def solicitar():
    item_id = request.form.get('item_id')
    cantidad = request.form.get('cantidad')

    item = Item.query.get(item_id)

    nueva = Solicitud(
        usuario=current_user.username,
        item_id=item_id,
        cantidad=int(cantidad),
        estado='pendiente'
    )

    db.session.add(nueva)
    db.session.commit()

    # 📧 Notificar admin
    try:
        msg = Message(
            subject='Nueva solicitud de inventario',
            recipients=['informatica@microgeo.cl']
        )
        msg.body = f"""
Nueva solicitud:

Usuario: {current_user.username}
Correo: {current_user.email}
Producto: {item.nombre}
Cantidad: {cantidad}
        """
        mail.send(msg)
    except Exception as e:
        print("Error mail admin:", e)

    return redirect('/inventario')


# 👨‍💻 SOLICITUDES ADMIN
@app.route('/solicitudes')
@login_required
def solicitudes():
    if current_user.role != 'admin':
        return "No autorizado"

    solicitudes = Solicitud.query.all()
    items = {item.id: item.nombre for item in Item.query.all()}

    return render_template('solicitudes.html', solicitudes=solicitudes, items=items)


# 👤 MIS SOLICITUDES
@app.route('/mis_solicitudes')
@login_required
def mis_solicitudes():
    solicitudes = Solicitud.query.filter_by(usuario=current_user.username).all()
    items = {item.id: item.nombre for item in Item.query.all()}

    return render_template('mis_solicitudes.html', solicitudes=solicitudes, items=items)


# ✅ APROBAR
@app.route('/aprobar/<int:id>')
@login_required
def aprobar(id):
    if current_user.role != 'admin':
        return "No autorizado"

    solicitud = Solicitud.query.get(id)
    item = Item.query.get(solicitud.item_id)

    if item.cantidad >= solicitud.cantidad:
        item.cantidad -= solicitud.cantidad
        solicitud.estado = 'aprobado'
    else:
        solicitud.estado = 'rechazado'

    db.session.commit()

    return redirect('/solicitudes')


# ❌ RECHAZAR
@app.route('/rechazar/<int:id>')
@login_required
def rechazar(id):
    if current_user.role != 'admin':
        return "No autorizado"

    solicitud = Solicitud.query.get(id)
    solicitud.estado = 'rechazado'

    db.session.commit()

    return redirect('/solicitudes')


# 🚪 LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')

            nuevo_admin = User(
                username='admin',
                email='admin@microgeo.cl',
                password=hashed_password,
                role='admin'
            )

            db.session.add(nuevo_admin)
            db.session.commit()

            print("✅ Admin creado")

    app.run(host='0.0.0.0', port=10000, debug=True)