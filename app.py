from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db
from routes.users import users_bp
from routes.attendance import attendance_bp
from routes.recognition import recognition_bp
from routes.auth import auth_bp
from routes.training import training_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'local-demo-secret-key'

CORS(app)
db.init_app(app)
JWTManager(app)

app.register_blueprint(auth_bp,        url_prefix='/api/auth')
app.register_blueprint(users_bp,       url_prefix='/api/users')
app.register_blueprint(attendance_bp,  url_prefix='/api/attendance')
app.register_blueprint(recognition_bp, url_prefix='/api/recognize')
app.register_blueprint(training_bp,    url_prefix='/api/training')

# Add these three page routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)