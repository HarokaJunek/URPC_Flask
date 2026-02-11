from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================

app = Flask(__name__)

# Секретный ключ для подписи сессий
# ВНИМАНИЕ: В продакшене используйте случайный сложный ключ!
app.secret_key = 'your-secret-key-123-change-this'

# База будет искаться в папке instance рядом с main.py
DATABASE = os.path.join('instance', 'nagruzka_DEMO.db')



@app.route('/')
def index():
    return render_template('index.html')



if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("❌ Ошибка базы данных: База данных не найдена")
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)