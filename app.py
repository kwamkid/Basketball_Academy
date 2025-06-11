from flask import Flask
from flask_login import LoginManager
import firebase_admin
from firebase_admin import credentials, firestore
import os
from config import Config
from models import User
from utils.filters import register_filters
from utils.helpers import init_default_admin

# Initialize Flask
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Firebase
try:
    if os.path.exists('serviceAccountKey.json'):
        # Local development
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            'projectId': Config.FIREBASE_PROJECT_ID
        })
    else:
        # Production on Cloud Run
        firebase_admin.initialize_app(options={
            'projectId': Config.FIREBASE_PROJECT_ID
        })
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    try:
        firebase_admin.initialize_app()
    except:
        pass

# Initialize Firestore
db = firestore.client()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อนใช้งาน'

@login_manager.user_loader
def load_user(user_id):
    user_doc = db.collection('users').document(user_id).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return User(user_id, data['username'], data.get('role', 'admin'))
    return None

# Register custom Jinja2 filters
register_filters(app)

# Register Blueprints
from routes.auth import auth_bp
from routes.main import main_bp
from routes.students import students_bp
from routes.parents import parents_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(students_bp)
app.register_blueprint(parents_bp)
app.register_blueprint(admin_bp)

# Initialize default admin user
with app.app_context():
    init_default_admin(db)

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=Config.PORT)