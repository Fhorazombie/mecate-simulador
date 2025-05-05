from flask import Flask, redirect, url_for, jsonify, request, session
from flask_dance.contrib.google import make_google_blueprint, google
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from models import db, User, Progress
from datetime import datetime
import os
from dotenv import load_dotenv

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'secret-dark-romantico')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-romantic-key')
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

db.init_app(app)
jwt = JWTManager(app)


# Google OAuth setup
google_bp = make_google_blueprint(
    scope=[
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
    ],
)
app.register_blueprint(google_bp, url_prefix="/login")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# ✨ Ruta principal
@app.route('/')
def index():
    return '👩‍💻 Casa Mecate Backend con JWT está vivo'

# 🔐 Login con Google + generación de JWT
@app.route('/auth/google')
def login_google():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({"error": "No se pudo autenticar con Google"}), 400

    info = resp.json()
    correo = info["email"]
    nombre = info.get("name", correo.split("@")[0])

    user = User.query.filter_by(correo=correo).first()
    if not user:
        user = User(nombre=nombre, correo=correo)
        db.session.add(user)
        db.session.commit()

    access_token = create_access_token(identity=user.id)
    return jsonify({
        "mensaje": f"Bienvenido {user.nombre}",
        "access_token": access_token
    })

@app.route("/logout")
def logout():
    session.clear()
    return redirect("http://localhost:4200/login") 

# 🧍 Obtener perfil autenticado
@app.route('/yo', methods=['GET'])
@jwt_required()
def yo():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({
        "id": user.id,
        "nombre": user.nombre,
        "correo": user.correo,
        "fecha_registro": user.fecha_registro.isoformat()
    })

# 📝 Registrar progreso
@app.route('/progreso', methods=['POST'])
@jwt_required()
def registrar_progreso():
    user_id = get_jwt_identity()
    data = request.json
    nuevo = Progress(
        usuario_id=user_id,
        modulo=data['modulo'],
        puntaje=data['puntaje']
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Progreso guardado"}), 201

# 📊 Consultar progreso
@app.route('/progreso', methods=['GET'])
@jwt_required()
def ver_progreso():
    user_id = get_jwt_identity()
    progreso = Progress.query.filter_by(usuario_id=user_id).all()
    return jsonify([{
        "modulo": p.modulo,
        "puntaje": p.puntaje,
        "fecha_completado": p.fecha_completado.isoformat()
    } for p in progreso])
