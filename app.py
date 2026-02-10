from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
#подключение бд(таня)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nagruzka_DEMO.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
#таня

@app.route('/')
def index():
    return render_template('index.html')



if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5001)