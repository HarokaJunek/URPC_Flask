from platform import machine
from unittest import case
from xml.parsers.expat import errors

from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

# ============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ!!wdfw
# ============================================================================

app = Flask(__name__)

# Секретный ключ для подписи сессий
# ВНИМАНИЕ: В продакшене используйте случайный сложный ключ!
app.secret_key = 'your-secret-key-123-change-this'

# База будет искаться в папке instance рядом с main.py
DATABASE = os.path.join('instance', 'nagruzka_DEMO.db')


#lololololo
# я делаю вдох так пахнет диор.......
# я искал тебя вечность....
#вот идиот.....
#дураddddd
# ============================================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ============================================================================

def get_db_connection():
    """
    Устанавливает соединение с базой данных.

    Возвращает:
        connection object с row_factory = sqlite3.Row
        Это позволяет обращаться к колонкам по имени: row['username']

    Важно: Мы предполагаем, что БД и таблицы уже созданы вручную!
    """
    conn = sqlite3.connect(DATABASE)

    # Устанавливаем row_factory для удобного доступа к данным
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================================
# 5. РЕАЛИЗАЦИЯ РЕГИСТРАЦИИ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Обработка регистрации нового пользователя.

    GET: Показывает форму регистрации
    POST: Принимает данные, валидирует и сохраняет в БД

    Процесс:
    1. Получение данных из формы
    2. Валидация (проверка корректности)
    3. Проверка уникальности в БД
    4. Хеширование пароля
    5. Сохранение в таблицы users и profiles
    6. Уведомление пользователя о результате
    """

    # Если пользователь уже авторизован - перенаправляем на главную
    if 'user_id' in session:
        flash('Вы уже авторизованы! Для создания нового аккаунта выйдите из системы.', 'info')
        return redirect(url_for('index'))

    # ============================================
    # ОБРАБОТКА POST-ЗАПРОСА (отправка формы)
    # ============================================
    if request.method == 'POST':

        # 1. ПОЛУЧАЕМ ДАННЫЕ ИЗ ФОРМЫ
        # Используем .get() для безопасного получения данных
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirmPassword', '')
        full_name = request.form.get('fullName', '')
        phone = request.form.get('phone', '')

        # ============================================
        # 2. ВАЛИДАЦИЯ ДАННЫХ (проверка корректности)
        # ============================================
        errors = []

        # --- Проверка имени пользователя ---
        if not username:
            errors.append('Имя пользователя обязательно для заполнения')
        elif len(username) < 3:
            errors.append('Имя пользователя должно быть не менее 3 символов')
        elif len(username) > 20:
            errors.append('Имя пользователя должно быть не более 20 символов')
        elif not username.replace('_', '').isalnum():
            errors.append('Имя пользователя может содержать только буквы, цифры и подчеркивание')

        # --- Проверка email ---
        if not email:
            errors.append('Email обязателен для заполнения')
        elif '@' not in email or '.' not in email:
            errors.append('Введите корректный email адрес')
        elif len(email) > 100:
            errors.append('Email слишком длинный')

        # --- Проверка пароля ---
        if not password:
            errors.append('Пароль обязателен для заполнения')
        elif len(password) < 6:
            errors.append('Пароль должен быть не менее 6 символов')
        elif password != confirm_password:
            errors.append('Пароли не совпадают')

        # --- Проверка ФИО ---
        if not full_name:
            errors.append('ФИО обязателен для заполнения')

        # Если есть ошибки валидации - показываем их
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')

        # ============================================
        # 3. ПРОВЕРКА УНИКАЛЬНОСТИ В БАЗЕ ДАННЫХ
        # ============================================

        # Устанавливаем соединение с БД
        conn = get_db_connection()

        try:
            # Проверяем, существует ли пользователь с таким username
            existing_user = conn.execute(
                'SELECT id_user FROM users WHERE login = ?',
                (username,)
            ).fetchone()

            if existing_user:
                flash('Пользователь с таким логином уже существует!', 'danger')
                conn.close()
                return render_template('register.html')

            # Проверяем, существует ли пользователь с таким email
            existing_email = conn.execute(
                'SELECT id_user FROM users WHERE email = ?',
                (email,)
            ).fetchone()

            if existing_email:
                flash('Пользователь с таким email уже существует!', 'danger')
                conn.close()
                return render_template('register.html')


            # ============================================
            # 4. ХЕШИРОВАНИЕ ПАРОЛЯ
            # ============================================

            # Генерируем безопасный хеш пароля
            # werkzeug.security автоматически добавляет "соль" (salt) для защиты
            password_hash = generate_password_hash(password)

            # ============================================
            # 5. СОХРАНЕНИЕ В БАЗУ ДАННЫХ
            # ============================================

            # Начинаем транзакцию для атомарности операций
            conn.execute('BEGIN TRANSACTION')

            try:
                # 5.1. Сохраняем в таблицу users
                cursor = conn.cursor()
                cursor.execute('''
                               INSERT INTO users (login, email, password, phone, full_name, created_at)
                               VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                               ''', (username, email, password_hash, phone, full_name))
                # Подтверждаем транзакцию
                conn.commit()

                # ============================================
                # 6. УВЕДОМЛЕНИЕ ОБ УСПЕХЕ
                # ============================================
                flash(f'Регистрация успешна! Добро пожаловать, {full_name}!', 'success')
                flash('Теперь вы можете войти в систему.', 'info')

                # Перенаправляем на страницу входа
                return redirect(url_for('index'))

            except sqlite3.Error as e:
                # Откатываем транзакцию при ошибке
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template('register.html')

        except sqlite3.Error as e:
            flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
            flash(f'Ошибка БД: {str(e)}', 'danger')
            return render_template('register.html')

        finally:
            # Всегда закрываем соединение с БД
            conn.close()

    # ============================================
    # ОБРАБОТКА GET-ЗАПРОСА (показ формы)
    # ============================================
    return render_template('register.html')








@app.route('/',methods=['GET', 'POST'])
def index():
    # ============================================
    # ОБРАБОТКА POST-ЗАПРОСА (отправка формы)
    # ============================================
    if request.method == 'POST':
        # 1. ПОЛУЧАЕМ ДАННЫЕ ИЗ ФОРМЫ
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        print(f"📥 Получены данные для входа:")
        print(f"   Логин: {login_input}")
        print(f"   Пароль: {'*' * len(password)}")

        # ============================================
        # 2. ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ
        # ============================================
        errors = []

        if not login_input:
            errors.append('Введите имя пользователя или email')
        if not password:
            errors.append('Введите пароль')

        # ============================================
        # 3. ПОИСК ПОЛЬЗОВАТЕЛЯ В БАЗЕ ДАННЫХ
        # ============================================

        # Устанавливаем соединение с БД
        conn = get_db_connection()

        try:
            # Ищем пользователя по username ИЛИ email
            # Пользователь может ввести любое из двух
            user = conn.execute('''
                                    SELECT id_user, full_name, email, login, password, id_role, kol_auth
                                    FROM users
                                    WHERE login = ?
                                       OR email = ?
                                    ''', (login_input, login_input,)).fetchone()

            # Если пользователь не найден
            if not user:
                # Не говорим точно, что не так (логин или пароль)
                # Это стандартная практика безопасности
                flash('Неверное имя пользователя/email или пароль', 'danger')
                conn.close()
                return render_template('index.html')


            # ============================================
            # 4. ПРОВЕРКА ПАРОЛЯ
            # ============================================

            # check_password_hash сравнивает введенный пароль с хешем из БД
            # Возвращает True если пароль верный, False если нет
            if not check_password_hash(user['password'], password):
                # Та же самая ошибка для безопасности
                flash('Неверное имя пользователя/email или пароль', 'danger')
                conn.close()
                return render_template('index.html')

            # ============================================
            # 5. СОЗДАНИЕ СЕССИИ ПОЛЬЗОВАТЕЛЯ
            # ============================================

            # Flask сессии хранятся в зашифрованных куках на стороне клиента
            # Важно: не храните чувствительные данные в сессии!

            session['user_id'] = user['id_user']
            session['username'] = user['login']
            session['email'] = user['email']
            session['full_name'] = user['full_name']
            match int(user['id_role']):
                case 1:
                    session['is_guest'] = True
                case 2:
                    session['is_admin'] = True
                case 3:
                    session['is_zav'] = True
                case 4:
                    session['is_prepod'] = True
                case 5:
                    session['is_specialist'] = True
                case _:
                    session['is_guest'] = False
                    session['is_admin'] = False
                    session['is_zav'] = False
                    session['is_prepod'] = False
                    session['is_specialist'] = False

            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


            try:
                # 5.1. Сохраняем в таблицу users
                cursor = conn.cursor()
                cursor.execute('''
                               UPDATE users SET
                               kol_auth = ?, last_auth = ?
                                WHERE id_user = ?
                               ''', (int(user['kol_auth']) + 1, session['login_time'], session['user_id']))
                # Подтверждаем транзакцию
                conn.commit()
            except sqlite3.Error as e:
                # Откатываем транзакцию при ошибке
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')

            print(f"✅ Пользователь найден:")
            print(f"   ID: {user['id_user']}")
            print(f"   Username: {user['login']}")

            # ============================================
            # 6. ОБНОВЛЕНИЕ ПОСЛЕДНЕЙ АКТИВНОСТИ (опционально)
            # ============================================
            # В реальных проектах часто добавляют поле last_login
            # conn.execute('UPDATE users SET last_login = datetime("now") WHERE id = ?', (user['id'],))
            # conn.commit()

            # ============================================
            # 7. УВЕДОМЛЕНИЕ И ПЕРЕНАПРАВЛЕНИЕ
            # ============================================

            flash(f'Добро пожаловать, {session['full_name']}!', 'success')

            # Проверяем, есть ли в запросе параметр 'next' (перенаправление после входа)
            next_page = request.args.get('next')

            if next_page:
                return redirect(next_page)


            # Перенаправляем в зависимости от роли
            #if user['is_admin']:
                print("🚀 Перенаправление в админ-панель")
                return redirect(url_for('admin_dashboard'))
            #else:
            print("🏠 Перенаправление на главную")
            return redirect(url_for('index'))

        except sqlite3.Error as e:
            flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
            return render_template('index.html')

        finally:
            # Всегда закрываем соединение с БД
            conn.close()

    # ============================================
    # ОБРАБОТКА GET-ЗАПРОСА (показ формы)
    # ============================================
    return render_template('index.html')

@app.route('/logout')
def logout():
    """
    Выход из системы - очистка сессии.

    Безопасный выход включает:
    1. Очистку всех данных сессии
    2. Сообщение пользователю
    3. Перенаправление на главную
    """

    # Проверяем, был ли пользователь авторизован
    if 'user_id' in session:
        username = session.get('username', 'Неизвестный')

        # Запоминаем данные для сообщения (перед очисткой)
        username = session.get('username', 'Пользователь')

        full_name = session['full_name']

        # ПОЛНАЯ очистка сессии
        session.clear()

        flash(f'Вы успешно вышли из системы. До свидания, {full_name}!', 'info')
    else:
        flash('Вы не были авторизованы.', 'warning')

    return redirect(url_for('index'))




@app.route('/load_table')
def load_table():
    if 'user_id' not in session:
        flash('Необходимо авторизоваться для доступа к этой странице.', 'warning')
        return redirect(url_for('index'))

    funck = request.args.get('funck')
    # Получаем поисковый запрос из параметров URL (если есть)
    search_query = request.args.get('search', '').strip()

    match funck:
        case 'edit_users':
            if session.get('is_admin', False) or session.get('is_specialist', False):
                conn = get_db_connection()
                # Базовый запрос (исключаем текущего пользователя)
                if session.get('is_admin', False):
                    query = '''
                        SELECT 
                            users.id_user,
                            users.full_name,
                            users.login,
                            users.email,
                            users.phone,
                            users.aktive,
                            users.created_at,
                            roles.role_name,
                            users.last_auth,
                            users.kol_auth
                        FROM users
                        LEFT JOIN roles ON users.id_role = roles.id_role
                        WHERE users.id_user != ?                '''
                    params = [session['user_id']]
                elif session.get('is_specialist', False):
                    query = '''
                        SELECT 
                            users.id_user,
                            users.full_name,
                            users.login,
                            users.email,
                            users.phone,
                            users.aktive,
                            users.created_at,
                            roles.role_name,
                            users.last_auth,
                            users.kol_auth
                        FROM users
                        LEFT JOIN roles ON users.id_role = roles.id_role
                        WHERE users.id_user != ? AND users.id_role = 4              '''
                    params = [session['user_id']]

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        users.full_name LIKE ? OR 
                        users.login LIKE ? OR 
                        users.email LIKE ?
                    )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern])

                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        case 'edit_disciplines':
            if session.get('is_specialist', False):
                conn = get_db_connection()

                # Базовый запрос
                query = 'SELECT * FROM disciplines'
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE disciplines.id_discipline LIKE ? OR disciplines.discipline_name LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()  # Используем fetchall() вместо execute_query()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))
#НАГРУЗКА!!!!!!!!!!!!
        case 'edit_nagruzka':
            if session.get('is_specialist', False):
                conn = get_db_connection()

                # Исправленный запрос - используем правильное название колонки form_name
                query = '''
                    SELECT 
                        w.id_load,
                        w.id_year,
                        w.id_teacher,
                        w.id_group,
                        w.id_discipline,
                        w.weeks_summer,
                        w.weeks_winter,
                        w.exam,
                        w.credit,
                        w.diff_credit,
                        w.independent_summer,
                        w.consultations_summer,
                        w.lectures_summer,
                        w.practice_summer,
                        w.labs_summer,
                        w.seminars_summer,
                        w.course_project_summer,
                        w.attestation_summer,
                        w.independent_winter,
                        w.consultations_winter,
                        w.lectures_winter,
                        w.practice_winter,
                        w.labs_winter,
                        w.seminars_winter,
                        w.course_project_winter,
                        w.attestation_winter,
                        d.discipline_name,
                        d.id_pck,
                        p.name_pck as pck_name,
                        u.full_name as teacher_name,
                        ay.year_name,
                        g.id_study_form,
                        sf.form_name as study_form
                    FROM workload w
                    JOIN disciplines d ON w.id_discipline = d.id_discipline
                    JOIN pck p ON d.id_pck = p.id_pck
                    JOIN users u ON w.id_teacher = u.id_user
                    JOIN academic_year ay ON w.id_year = ay.id_year
                    JOIN groups g ON w.id_group = g.id_group
                    JOIN study_form sf ON g.id_study_form = sf.id_form
                    ORDER BY ay.year_name DESC, d.discipline_name
                '''

                rows = conn.execute(query).fetchall()

                # Формируем данные для таблицы
                workload_data = []
                for row in rows:
                    # Расчет нагрузок
                    with_teacher_summer = (row['lectures_summer'] or 0) + (row['practice_summer'] or 0) + \
                                          (row['labs_summer'] or 0) + (row['seminars_summer'] or 0) + \
                                          (row['course_project_summer'] or 0)

                    with_teacher_winter = (row['lectures_winter'] or 0) + (row['practice_winter'] or 0) + \
                                          (row['labs_winter'] or 0) + (row['seminars_winter'] or 0) + \
                                          (row['course_project_winter'] or 0)

                    total_summer = (row['independent_summer'] or 0) + (
                                row['consultations_summer'] or 0) + with_teacher_summer
                    total_winter = (row['independent_winter'] or 0) + (
                                row['consultations_winter'] or 0) + with_teacher_winter

                    weekly_load_summer = round(total_summer / (row['weeks_summer'] or 1), 1) if row[
                        'weeks_summer'] else 0
                    weekly_load_winter = round(total_winter / (row['weeks_winter'] or 1), 1) if row[
                        'weeks_winter'] else 0

                    workload_data.append({
                        'id_load': row['id_load'],
                        'id_year': row['id_year'],
                        'year_name': row['year_name'],
                        'id_discipline': row['id_discipline'],
                        'discipline_name': row['discipline_name'],
                        'id_group': row['id_group'],
                        'study_form': row['study_form'],
                        'teacher_name': row['teacher_name'],
                        'pck_name': row['pck_name'],
                        'weeks_summer': row['weeks_summer'],
                        'weeks_winter': row['weeks_winter'],
                        'independent_summer': row['independent_summer'],
                        'consultations_summer': row['consultations_summer'],
                        'lectures_summer': row['lectures_summer'],
                        'practice_summer': row['practice_summer'],
                        'labs_summer': row['labs_summer'],
                        'seminars_summer': row['seminars_summer'],
                        'course_project_summer': row['course_project_summer'],
                        'attestation_summer': row['attestation_summer'],
                        'independent_winter': row['independent_winter'],
                        'consultations_winter': row['consultations_winter'],
                        'lectures_winter': row['lectures_winter'],
                        'practice_winter': row['practice_winter'],
                        'labs_winter': row['labs_winter'],
                        'seminars_winter': row['seminars_winter'],
                        'course_project_winter': row['course_project_winter'],
                        'attestation_winter': row['attestation_winter'],
                        'total_summer': total_summer,
                        'total_winter': total_winter,
                        'with_teacher_summer': with_teacher_summer,
                        'with_teacher_winter': with_teacher_winter,
                        'weekly_load_summer': weekly_load_summer,
                        'weekly_load_winter': weekly_load_winter,
                        'total_load': total_summer + total_winter
                    })

                # Получаем список учебных годов для фильтра
                academic_years = conn.execute(
                    'SELECT id_year, year_name FROM academic_year ORDER BY year_name DESC'
                ).fetchall()

                conn.close()

                # Передаем данные в шаблон
                return render_template(
                    'load_table.html',
                    workload_data=workload_data,
                    academic_years=academic_years,
                    funck=funck
                )
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        case 'edit_years':
            if session.get('is_specialist', False):
                conn = get_db_connection()

                # Базовый запрос
                query = 'SELECT * FROM academic_year'
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE academic_year.id_year LIKE ? OR academic_year.year_name LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()  # Используем fetchall() вместо execute_query()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        case 'edit_fgoss':
            if session.get('is_specialist', False):
                conn = get_db_connection()

                # Базовый запрос
                query = 'SELECT * FROM fgoss'
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE fgoss.id_fgos LIKE ? OR fgoss.name LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()  # Используем fetchall() вместо execute_query()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        case 'edit_pck':
            if session.get('is_specialist', False):
                conn = get_db_connection()

                # Базовый запрос
                query = 'SELECT * FROM pck'
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE pck.id_pck LIKE ? OR pck.name_pck LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()  # Используем fetchall() вместо execute_query()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        
# ============================ СТУДЕНТЫ ================================ #

        case 'edit_students':

             # Проверка прав доступа
            if (session.get('is_zav', False)):
            
                # Установка соединения с базой данных
                conn = get_db_connection()

                # Запрос
                query = '''
                    SELECT 
                        students.id_student,
                        students.full_name,
                        groups.id_group
                    FROM students
                    INNER JOIN groups ON groups.id_group = students.id_group
                    '''
                
                # Список параметров для безопасной подстановки в запрос
                params = []

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        students.id_student LIKE ? OR
                        students.full_name LIKE ? OR
                        groups.id_group LIKE ? 
                        )'''

                    # Шаблон для поиска по подстроке
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern])

                # Выполнение запроса с параметрами
                table_info = conn.execute(query, params).fetchall()
                
                # Закрытие соединения с БД
                conn.close()

                # Отображение таблицы с полученными данными
                return render_template('load_table.html', table_info=table_info, funck=funck)
            
            else:
            
                # Сообщение об ошибке при отсутствии прав доступа
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

# ============================ ТИП ВЕДОМОСТИ ================================ #

        case 'edit_typesved':

             # Проверка прав доступа
            if (session.get('is_zav', False)):
            
                # Установка соединения с базой данных
                conn = get_db_connection()

                # Запрос
                query = '''
                    SELECT 
                        statement_types.id_type,
                        statement_types.type_name
                    FROM statement_types
                    '''
                
                # Список параметров для безопасной подстановки в запрос
                params = []

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        statement_types.id_type LIKE ? OR
                        statement_types.type_name LIKE ? 
                        )'''

                    # Шаблон для поиска по подстроке
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern])

                # Выполнение запроса с параметрами
                table_info = conn.execute(query, params).fetchall()
                
                # Закрытие соединения с БД
                conn.close()

                # Отображение таблицы с полученными данными
                return render_template('load_table.html', table_info=table_info, funck=funck)
            
            else:
            
                # Сообщение об ошибке при отсутствии прав доступа
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

# ============================ ГРУППЫ ================================ #

        case 'edit_groups':
            if (session.get('is_specialist', False) or session.get('is_zav', False)):
                conn = get_db_connection()

                # Базовый запрос - ИСПРАВЛЕНО: добавлены пробелы
                query = ('SELECT groups.id_group, groups.course_number, study_form.form_name, '
                         'users.id_user as class_teacher_id, users.full_name as teacher_name, '
                         'specialties.id_specialty as specialty_name '
                         'FROM groups '
                         'INNER JOIN users ON groups.id_class_teacher = users.id_user '
                         'INNER JOIN specialties ON groups.id_specialty = specialties.id_specialty '
                         'INNER JOIN study_form ON groups.id_study_form = study_form.id_form')
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE groups.id_group LIKE ? OR groups.course_number LIKE ? OR study_form.id_form LIKE ? OR users.full_name LIKE ? OR specialties.name_specialty LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern, like_pattern, like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

# ============================ ФОРМЫ ОБУЧЕНИЯ ================================ #

        case 'edit_formobuch':

             # Проверка прав доступа
            if (session.get('is_zav', False)):
            
                # Установка соединения с базой данных
                conn = get_db_connection()

                # Запрос
                query = '''
                    SELECT 
                        study_form.id_form,
                        study_form.form_name
                    FROM study_form
                    '''
                
                # Список параметров для безопасной подстановки в запрос
                params = []

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        study_form.id_form LIKE ? OR
                        study_form.form_name LIKE ? 
                        )'''

                    # Шаблон для поиска по подстроке
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern])

                # Выполнение запроса с параметрами
                table_info = conn.execute(query, params).fetchall()
                
                # Закрытие соединения с БД
                conn.close()

                # Отображение таблицы с полученными данными
                return render_template('load_table.html', table_info=table_info, funck=funck)
            
            else:
            
                # Сообщение об ошибке при отсутствии прав доступа
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))
            
# ============================ ФОРМЫ ОБУЧЕНИЯ ================================ #

        case 'edit_spec':

             # Проверка прав доступа
            if (session.get('is_zav', False)):
            
                # Установка соединения с базой данных
                conn = get_db_connection()

                # Запрос
                query = '''
                    SELECT 
                        specialties.id_specialty,
                        specialties.specialty_name,
                        specialties.id_department
                    FROM specialties
                    INNER JOIN departments ON specialties.id_department = departments.id_department
                    '''
                
                # Список параметров для безопасной подстановки в запрос
                params = []

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        specialties.id_specialty LIKE ? OR
                        specialties.specialty_name LIKE ? OR
                        departments.department_name LIKE ?
                        )'''

                    # Шаблон для поиска по подстроке
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern])

                # Выполнение запроса с параметрами
                table_info = conn.execute(query, params).fetchall()
                
                # Закрытие соединения с БД
                conn.close()

                # Отображение таблицы с полученными данными
                return render_template('load_table.html', table_info=table_info, funck=funck)
            
            else:
            
                # Сообщение об ошибке при отсутствии прав доступа
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))
            
        # Обработка других значений funck (если есть)
        case _:

            # Обработка неизвестного параметра функции
            flash('Неверный параметр функции', 'danger')
            return redirect(url_for('index'))
            


@app.route('/delete_recording/<path:id>', methods=['GET', 'POST'])
def delete_recording(id):
    """
    Удаление пользователя по ID.
    Доступно только администраторам. Нельзя удалить самого себя.
    """
    # Проверка авторизации
    if 'user_id' not in session:
        flash('Необходимо авторизоваться для доступа к этой странице.', 'warning')
        return redirect(url_for('index'))

    # Проверка прав администратора
    #if not session.get('is_admin', False):
        flash('У вас нет прав на удаление пользователей.', 'danger')
        return redirect(url_for('load_table', funck='edit_users'))

    #if not session.get('is_specialist', False):
        flash('У вас нет прав на удаление дисциплины.', 'danger')
        return redirect(url_for('load_table', funck='edit_disciplines'))

    # Проверка, что пользователь не пытается удалить себя
    #if session['user_id'] == id:
        flash('Нельзя удалить самого себя.', 'danger')
        return redirect(url_for('load_table', funck='edit_users'))

    try:
        funck = request.args.get('funck')
        conn = get_db_connection()

        match funck:
            case 'edit_users':
                if not session.get('is_admin', False) and not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление пользователей.', 'danger')
                    return redirect(url_for('load_table', funck='edit_users'))

                if session['user_id'] == id:
                    flash('Нельзя удалить самого себя.', 'danger')
                    return redirect(url_for('load_table', funck='edit_users'))

                # Вариант 1: Физическое удаление (удаление строки из таблицы)
                conn.execute('DELETE FROM users WHERE id_user = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_users'))

            case 'edit_disciplines':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление дисциплины.', 'danger')
                    return redirect(url_for('load_table', funck='edit_disciplines'))


                conn.execute('DELETE FROM disciplines WHERE id_discipline = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_disciplines'))

            case 'edit_pck':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление дисциплины.', 'danger')
                    return redirect(url_for('load_table', funck='edit_pck'))

                conn.execute('DELETE FROM pck WHERE id_pck = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_pck'))

            case 'edit_years':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление учебного года.', 'danger')
                    return redirect(url_for('load_table', funck='edit_years'))

                conn.execute('DELETE FROM academic_year WHERE id_year = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_years'))

            case 'edit_fgoss':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление учебного года.', 'danger')
                    return redirect(url_for('load_table', funck='edit_fgoss'))

                conn.execute('DELETE FROM fgoss WHERE id_fgos = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_fgoss'))
            

            # ============================ СТУДЕНТЫ ================================ #

            case 'edit_students':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление студента.', 'danger')
                    return redirect(url_for('load_table', funck='edit_students'))

                conn.execute('DELETE FROM students WHERE id_student = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_students'))
            

            # ==================== ВИДЫ ВЕДОМОСТИ ==================== #

            case 'edit_typesved':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление типа ведомости.', 'danger')
                    return redirect(url_for('load_table', funck='edit_typesved'))

                conn.execute('DELETE FROM statement_types WHERE id_type = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_typesved'))
            

            # ==================== ГРУППЫ ==================== #

            case 'edit_groups':
                if not (session.get('is_zav', False)):
                    flash('У вас нет прав на удаление группы.', 'danger')
                    return redirect(url_for('load_table', funck='edit_groups'))

                # ИСПРАВЛЕНО: groups -> id_group (название колонки)
                conn.execute('DELETE FROM groups WHERE id_group = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_groups'))
            

            # ==================== ФОРМА ОБУЧЕНИЯ ==================== #

            case 'edit_formobuch':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на формы обучения.', 'danger')
                    return redirect(url_for('load_table', funck='edit_formobuch'))

                conn.execute('DELETE FROM study_form WHERE id_form = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_formobuch'))
            

            # ==================== СПЕЦИАЛЬНОСТЬ ==================== #

            case 'edit_spec':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на формы обучения.', 'danger')
                    return redirect(url_for('load_table', funck='edit_spec'))

                conn.execute('DELETE FROM specialties WHERE id_specialty = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_spec'))

            # ==================== ВЕДОМОСТЬ (С ОЦЕНКАМИ) ==================== #

            case 'edit_ved':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на формы обучения.', 'danger')
                    return redirect(url_for('load_table', funck='edit_ved'))

                conn.execute('DELETE FROM statement WHERE id_statement = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_ved'))

            # Обработка других значений funck (если есть)
            case _:
                flash('Неверный параметр функции', 'danger')
                return redirect(url_for('index'))

    except sqlite3.IntegrityError as e:
        # Ошибка целостности - возможно, есть связанные записи
        conn.rollback()
        flash(f'Невозможно удалить запись: есть связанные данные. Ошибка: {str(e)}', 'danger')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Ошибка базы данных: {str(e)}', 'danger')
    finally:
        conn.close()

    #return redirect(url_for('load_table', funck='edit_users'))


@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    funck = request.args.get('funck') or request.form.get('funck')

    print(f"=== DEBUG ===")
    print(f"funck: {funck}")
    print(f"method: {request.method}")
    print(f"args: {dict(request.args)}")
    print(f"form: {dict(request.form)}")

    if not funck:
        flash('Не указан параметр функции', 'danger')
        return redirect(url_for('index'))

    if funck == 'edit_users':
        if session.get('is_admin', False) or session.get('is_specialist', False):
            # Вспомогательная функция для загрузки ролей из БД
            def get_roles():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_role, role_name FROM roles ORDER BY role_name').fetchall()
                conn.close()
                return [{'id': row['id_role'], 'name': row['role_name']} for row in rows]

            # GET-запрос: просто показываем форму со списком ролей
            if request.method == 'GET':
                roles = get_roles()
                return render_template('add_info.html', funck=funck, roles=roles)

            # POST-запрос: обработка отправленной формы
            # 1. Получаем данные
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirmPassword', '')
            full_name = request.form.get('fullName', '').strip()
            phone = request.form.get('phone', '').strip()
            if session.get('is_admin', False):
                role_id = request.form.get('role')

            # 2. Валидация
            errors = []

            # Логин
            if not username:
                errors.append('Имя пользователя обязательно')
            elif len(username) < 3:
                errors.append('Имя пользователя должно быть не менее 3 символов')
            elif len(username) > 20:
                errors.append('Имя пользователя должно быть не более 20 символов')
            elif not username.replace('_', '').isalnum():
                errors.append('Имя пользователя может содержать только буквы, цифры и подчёркивание')

            # Email
            if not email:
                errors.append('Email обязателен')
            elif '@' not in email or '.' not in email:
                errors.append('Введите корректный email')
            elif len(email) > 100:
                errors.append('Email слишком длинный')

            # Пароль
            if not password:
                errors.append('Пароль обязателен')
            elif len(password) < 6:
                errors.append('Пароль должен быть не менее 6 символов')
            elif password != confirm_password:
                errors.append('Пароли не совпадают')

            # ФИО
            if not full_name:
                errors.append('ФИО обязательно')

            # Роль: загружаем актуальный список для проверки
            roles = get_roles()
            if session.get('is_admin', False):
                valid_role_ids = [str(r['id']) for r in roles]
                if not role_id or role_id not in valid_role_ids:
                    errors.append('Выберите корректную роль')

            # Если есть ошибки — показываем форму снова
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    roles=roles
                )

            # 3. Проверка уникальности логина и email
            conn = get_db_connection()
            try:
                existing_user = conn.execute(
                    'SELECT id_user FROM users WHERE login = ?',
                    (username,)
                ).fetchone()
                if existing_user:
                    flash('Пользователь с таким логином уже существует', 'danger')
                    return render_template('add_info.html', funck=funck,
                                           form_data=request.form, roles=roles)

                existing_email = conn.execute(
                    'SELECT id_user FROM users WHERE email = ?',
                    (email,)
                ).fetchone()
                if existing_email:
                    flash('Пользователь с таким email уже существует', 'danger')
                    return render_template('add_info.html', funck=funck,
                                           form_data=request.form, roles=roles)

                # 4. Хеширование пароля
                password_hash = generate_password_hash(password)

                # 5. Вставка нового пользователя
                conn.execute('BEGIN TRANSACTION')
                try:
                    cursor = conn.cursor()
                    if session.get('is_admin', False):
                        cursor.execute('''
                            INSERT INTO users 
                            (login, email, password, phone, full_name, created_at, id_role)
                            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), ?)
                        ''', (username, email, password_hash, phone, full_name, int(role_id)))
                    elif session.get('is_specialist', False):
                        cursor.execute('''
                            INSERT INTO users 
                            (login, email, password, phone, full_name, created_at, id_role)
                            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), 4)
                        ''', (username, email, password_hash, phone, full_name))
                    conn.commit()
                    flash(f'Пользователь {full_name} успешно создан!', 'success')
                    return redirect(url_for('load_table', funck='edit_users'))
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                    return render_template('add_info.html', funck=funck,
                                           form_data=request.form, roles=roles)
            except sqlite3.Error as e:
                flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                return render_template('add_info.html', funck=funck,
                                       form_data=request.form, roles=roles)
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления пользователя', 'danger')
            return redirect(url_for('index'))

    if funck == 'edit_disciplines':
        if session.get('is_specialist', False):
            # Вспомогательная функция для загрузки PCK из БД
            def get_pck():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_pck, name_pck FROM pck ORDER BY name_pck').fetchall()
                conn.close()
                return [{'id': row['id_pck'], 'name': row['name_pck']} for row in rows]

            # GET-запрос: просто показываем форму со списком PCK
            if request.method == 'GET':
                pck_list = get_pck()
                return render_template('add_info.html', funck=funck, pck_list=pck_list)

            # POST-запрос: обработка отправленной формы
            # 1. Получаем данные
            discipline_id = request.form.get('discipline_id', '').strip()
            discipline_name = request.form.get('discipline_name', '').strip()
            id_pck = request.form.get('id_pck')

            # 2. Валидация
            errors = []

            # ID дисциплины
            if not discipline_id:
                errors.append('ID дисциплины обязательно')
            elif len(discipline_id) > 50:
                errors.append('ID дисциплины должен быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z0-9.]+$', discipline_id):
                errors.append('ID дисциплины может содержать только буквы (русские/латинские), цифры и точки')

            # Название дисциплины
            if not discipline_name:
                errors.append('Название дисциплины обязательно')
            elif len(discipline_name) > 50:
                errors.append('Название дисциплины должно быть не более 50 символов')

            # Загружаем список PCK для проверки
            pck_list = get_pck()
            valid_pck_ids = [str(p['id']) for p in pck_list]
            if not id_pck or id_pck not in valid_pck_ids:
                errors.append('Выберите корректный ПЦК')

            # Если есть ошибки — показываем форму снова
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    pck_list=pck_list
                )

            # 3. Проверка уникальности ID дисциплины
            conn = get_db_connection()
            try:
                existing_discipline = conn.execute(
                    'SELECT id_discipline FROM disciplines WHERE id_discipline = ?',
                    (discipline_id,)
                ).fetchone()
                if existing_discipline:
                    flash('Дисциплина с таким ID уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        pck_list=pck_list
                    )

                # Проверка уникальности названия дисциплины
                existing_name = conn.execute(
                    'SELECT id_discipline FROM disciplines WHERE discipline_name = ?',
                    (discipline_name,)
                ).fetchone()
                if existing_name:
                    flash('Дисциплина с таким названием уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        pck_list=pck_list
                    )

                # 4. Вставка новой дисциплины
                conn.execute('BEGIN TRANSACTION')
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO disciplines 
                        (id_discipline, discipline_name, id_pck)
                        VALUES (?, ?, ?)
                    ''', (discipline_id, discipline_name, int(id_pck)))
                    conn.commit()
                    flash(f'Дисциплина {discipline_name} успешно создана!', 'success')
                    return redirect(url_for('load_table', funck='edit_disciplines'))
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        pck_list=pck_list
                    )
            except sqlite3.Error as e:
                flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    pck_list=pck_list
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления дисциплины', 'danger')
            return redirect(url_for('index'))

    if funck == 'edit_years':
        if session.get('is_specialist', False):
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)

            year_name = request.form.get('year_name', '').strip()
            errors = []

            if not year_name:
                errors.append('Название учебного года обязательно')
            elif len(year_name) > 50:
                errors.append('Название учебного года должно быть не более 50 символов')
            elif not re.match(r'^\d{4}-\d{4}$', year_name):
                errors.append('Название учебного года должно быть в формате ГГГГ-ГГГГ (например, 2023-2024)')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )

            # Работа с БД
            conn = get_db_connection()
            try:
                # Проверка уникальности
                existing_year = conn.execute(
                    'SELECT id_year FROM academic_year WHERE year_name = ?',
                    (year_name,)
                ).fetchone()

                if existing_year:
                    flash('Такой учебный год уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка нового учебного года
                conn.execute(
                    'INSERT INTO academic_year (year_name) VALUES (?)',
                    (year_name,)
                )
                conn.commit()
                flash(f'Учебный год {year_name} успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_years'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления учебного года', 'danger')
            return redirect(url_for('index'))

    if funck == 'edit_fgoss':
        if session.get('is_specialist', False):
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)

            fgos_name = request.form.get('fgos_name', '').strip()
            errors = []

            if not fgos_name:
                errors.append('Название ФГОС обязательно')
            elif len(fgos_name) > 50:
                errors.append('Название ФГОС должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.]+$', fgos_name):
                errors.append(
                    'Название ФГОС может содержать буквы (русские/латинские), цифры, пробелы, дефисы и точки')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )

            # Работа с БД
            conn = get_db_connection()
            try:
                # Проверка уникальности
                existing_fgos = conn.execute(
                    'SELECT id_fgos FROM fgoss WHERE name = ?',
                    (fgos_name,)
                ).fetchone()

                if existing_fgos:
                    flash('Такой ФГОС уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка нового ФГОС
                conn.execute(
                    'INSERT INTO fgoss (name) VALUES (?)',
                    (fgos_name,)
                )
                conn.commit()
                flash(f'ФГОС {fgos_name} успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_fgoss'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления ФГОС', 'danger')
            return redirect(url_for('index'))

    if funck == 'edit_pck':
        if session.get('is_specialist', False):
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)

            pck_name = request.form.get('pck_name', '').strip()
            errors = []

            if not pck_name:
                errors.append('Название ПЦК обязательно')
            elif len(pck_name) > 50:
                errors.append('Название ПЦК должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.]+$', pck_name):
                errors.append(
                    'Название ПЦК может содержать буквы (русские/латинские), цифры, пробелы, дефисы и точки')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )

            # Работа с БД
            conn = get_db_connection()
            try:
                # Проверка уникальности
                existing_pck = conn.execute(
                    'SELECT id_pck FROM pck WHERE name_pck = ?',
                    (pck_name,)
                ).fetchone()

                if existing_pck:
                    flash('Такое ПЦК уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка нового ПЦК
                conn.execute(
                    'INSERT INTO pck (name_pck) VALUES (?)',
                    (pck_name,)
                )
                conn.commit()
                flash(f'ПЦК {pck_name} успешно создано!', 'success')
                return redirect(url_for('load_table', funck='edit_pck'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления ПЦК', 'danger')
            return redirect(url_for('index'))
        
# ============================ СТУДЕНТЫ ================================ #    
    
    if funck == 'edit_students':
        if session.get('is_zav', False):

            # форма обучения
            def get_groups():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                conn.close()
                return [{'id': row['id_group']} for row in rows]

            if request.method == 'GET':
                groups = get_groups()
                return render_template('add_info.html', funck=funck, groups=groups)
  
            # POST-запрос: обработка отправленной формы
            # 1. Получаем данные
            full_name = request.form.get('full_name', '')
            id_group = request.form.get('id_group')
            
            # 2. Валидация
            errors = []

            # ФИО            
            if not full_name:
                errors.append('ФИО обязательно')
            elif len(full_name) > 50:
                errors.append('ФИО должно быть не более 100 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z\s]+$', full_name):
                errors.append('ФИО может содержать буквы (русские/латинские) и пробелы')

            # Номер группы
            groups = get_groups()
            if session.get('is_zav', False):
                valid_group_ids = [str(g['id']) for g in groups]
                if not id_group or id_group not in valid_group_ids:
                    errors.append('Выберите корректную группу')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    groups=groups
                )
            
#  ПРОВЕРКА УНИКАЛЬНОСТИ ЗАПИСИ #


            # 5. Вставка новой записи
            conn.execute('BEGIN TRANSACTION')
            try:
                    cursor = conn.cursor()
                    if session.get('is_zav', False):
                        cursor.execute('''
                            INSERT INTO groups 
                            (full_name, id_group)
                            VALUES (?, ?)
                        ''', (full_name, id_group))
            
                    conn.commit()
                    flash(f'Студент {full_name} успешно создан!', 'success')
                    return redirect(url_for('load_table', funck='edit_students'))
            
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                return render_template('add_info.html', funck=funck,
                                           form_data=request.form, groups=groups)
            
            except sqlite3.Error as e:
                flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                return render_template('add_info.html', funck=funck,
                                    form_data=request.form, groups=groups)
            
            finally:
                conn.close()
        
        else:
            flash('У вас нет прав для добавления студента', 'danger')
            return redirect(url_for('index'))

    

# ============================ ВИДЫ ВЕДОМОСТИ ================================ #   

    if funck == 'edit_typesved':

        if session.get('is_zav', False):

            # Если метод запроса GET - показываем форму для добавления
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)

            type_name = request.form.get('type_name', '').strip()
            errors = []

            if not type_name:
                errors.append('Название типа ведомости обязательно')
            elif len(type_name) > 50:
                errors.append('Название типа ведомости должно быть не более 50 символов')
            elif not type_name.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.]+$', type_name):
                errors.append(
                    'Название типа ведомости может содержать буквы (русские/латинские), цифры, пробелы, дефисы и точки')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            

            #  ПРОВЕРКА УНИКАЛЬНОСТИ ЗАПИСИ #
            conn = get_db_connection()
            try:
                # Проверка уникальности
                existing_type = conn.execute(
                    'SELECT id_type FROM statement_types WHERE type_name = ?',
                    (type_name)
                ).fetchone()

                if existing_type:
                    flash('Такой тип ведомости уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка новой записи
                conn.execute(
                    'INSERT INTO statement_types (type_name) VALUES (?)',
                    (type_name)
                )
                conn.commit()
                flash(f'Тип ведомости {type_name} успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_typesved'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления типа ведомости', 'danger')
            return redirect(url_for('index'))

#============================ ГРУППЫ ================================ #

    if funck == 'edit_groups':
        if session.get('is_zav', False):

            # форма обучения
            def get_forms():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_form, form_name FROM study_form ORDER BY form_name').fetchall()
                conn.close()
                return [{'id': row['id_form'], 'name': row['form_name']} for row in rows]

            if request.method == 'GET':
                forms = get_forms()
                return render_template('add_info.html', funck=funck, forms=forms)
            
            # препод
            def get_prepod():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name').fetchall()
                conn.close()
                return [{'id': row['id_user'], 'name': row['full_name']} for row in rows]

            if request.method == 'GET':
                prepods = get_prepod()
                return render_template('add_info.html', funck=funck, prepods=prepods)

            # специальность
            def get_specs():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_specialty, specialty_name FROM specialties ORDER BY specialty_name').fetchall()
                conn.close()
                return [{'id': row['id_specialty'], 'name': row['specialty_name']} for row in rows]

            if request.method == 'GET':
                specs = get_specs()
                return render_template('add_info.html', funck=funck, specs=specs)

            # POST-запрос: обработка отправленной формы
            # 1. Получаем данные
            id_group = request.form.get('group', '')
            course_num = request.form.get('course_num', '')
            form_id = request.form.get('formobuch')
            prepod_id = request.form.get('prepod')
            spec_id = request.form.get('spec')
            
            # 2. Валидация
            errors = []

            # Номер группы
            if not id_group:
                errors.append('Номер группы обязателен')
            elif len(id_group) > 50:
                errors.append('Номер группы должно быть не более 50 символов')
            elif not re.match(r'^\d{1,3}/[А-Яа-я]{1,5}-\d{1,4}[А-Яа-я]{0,3}$', id_group):
                errors.append('Неверный формат. Пример: 22/ИП-491 или 22/ИП-491кв')
           
            # Номер курса
            if not course_num:
                errors.append('Номер курса обязателен')
            elif not course_num.isdigit():
                errors.append('Номер курса должен быть цифрой')
            else:
                course_num = int(course_num)
                if course_num not in range(1, 6):
                    errors.append('Номер курса должен быть от 1 до 5')

            # форма обучения
            forms = get_forms()
            if session.get('is_zav', False):
                valid_form_ids = [str(f['id']) for f in forms]
                if not form_id or form_id not in valid_form_ids:
                    errors.append('Выберите корректную форму')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    forms=forms
                )
            
            # преподы
            prepod = get_prepod()
            if session.get('is_zav', False):
                valid_prepod_ids = [str(p['id']) for p in prepods]
                if not prepod_id or prepod_id not in valid_prepod_ids:
                    errors.append('Выберите корректного преподавателя')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    prepods=prepods
                )

            # специальность
            specs = get_specs()
            if session.get('is_zav', False):
                valid_spec_ids = [str(s['id']) for s in specs]
                if not spec_id or spec_id not in valid_spec_ids:
                    errors.append('Выберите корректную специальность')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    specs=specs
                )
            
#  ПРОВЕРКА УНИКАЛЬНОСТИ ЗАПИСИ #
            


            # 5. Вставка новой записи
            conn.execute('BEGIN TRANSACTION')
            try:
                    cursor = conn.cursor()
                    if session.get('is_zav', False):
                        cursor.execute('''
                            INSERT INTO groups 
                            (id_group, course_number, id_study_form, , id_class_teacher, id_specialty)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (id_group, course_num, int(form_id), int(prepod_id), int(spec_id)))
            
                    conn.commit()
                    flash(f'Группа {id_group} успешно создан!', 'success')
                    return redirect(url_for('load_table', funck='edit_groups'))
            
            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                return render_template('add_info.html', funck=funck,
                                           form_data=request.form, prepods=prepods, specs=specs, forms=forms)
            except sqlite3.Error as e:
                flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                return render_template('add_info.html', funck=funck,
                                    form_data=request.form, prepods=prepods, specs=specs, forms=forms)
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления пользователя', 'danger')
            return redirect(url_for('index'))

    
# ============================ ФОРМА ОБУЧЕНИЯ ================================ #

    if funck == 'edit_formobuch':

        if session.get('is_zav', False):

            # Если метод запроса GET - показываем форму для добавления
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)


            form_name = request.form.get('form_name', '').strip()
            errors = []

            if not form_name:
                errors.append('Название формы обучения обязательно')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )

            # Работа с БД
            conn = get_db_connection()
            try:
                # Проверка уникальности
                existing_form = conn.execute(
                    'SELECT id_form FROM study_form WHERE form_name = ?',
                    (form_name)
                ).fetchone()

                if existing_form:
                    flash('Такая форма обучения уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка новой записи
                conn.execute(
                    'INSERT INTO study_form (form_name) VALUES (?)',
                    (form_name)
                )
                conn.commit()
                flash(f'Форма обучения {form_name} успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_formobuch'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления форм обучения', 'danger')
            return redirect(url_for('index'))

# ============================ СПЕЦИАЛЬНОСТИ ================================ #

    if funck == 'edit_spec':
            if session.get('is_zav', False):

                # форма обучения
                def get_departs():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                    conn.close()
                    return [{'id': row['id_department'], 'name': row['department_name']} for row in rows]

                if request.method == 'GET':
                    departs = get_departs()
                    return render_template('add_info.html', funck=funck, departs=departs)
                

                # POST-запрос: обработка отправленной формы
                # 1. Получаем данные
                id_specialty = request.form.get('id_specialty', '')
                specialty_name = request.form.get('specialty_name', '')
                id_department = request.form.get('id_department')
                
                # 2. Валидация
                errors = []

                # Номер группы
                if not id_specialty:
                    errors.append('Код специальности обязателен')
                elif not re.match(r'^\d{2}\.\d{2}\.\d{2}$', id_specialty):
                    errors.append('Неверный формат специальности. Пример: 38.02.01')
            
                # Название специальности
                if not specialty_name:
                    errors.append('Название специальности обязательно')
                elif len(specialty_name) > 50:
                    errors.append('Название специальности должно быть не более 50 символов')

                # форма обучения
                departs = get_departs()
                if session.get('is_zav', False):
                    valid_dept_ids = [str(d['id']) for d in departs]
                    if not id_department or id_department not in valid_dept_ids:
                        errors.append('Выберите корректное отделение')

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        departs=departs
                    )
                
#  ПРОВЕРКА УНИКАЛЬНОСТИ ЗАПИСИ #

                # 5. Вставка новой записи
                conn.execute('BEGIN TRANSACTION')
                try:
                        cursor = conn.cursor()
                        if session.get('is_zav', False):
                            cursor.execute('''
                                INSERT INTO groups 
                                (id_specialty, specialty_name, id_department)
                                VALUES (?, ?, ?)
                            ''', (id_specialty, specialty_name, int(id_department)))

                        conn.commit()
                        flash(f'Группа {id_specialty} успешно создана!', 'success')
                        return redirect(url_for('load_table', funck='edit_spec'))
                
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                    return render_template('add_info.html', funck=funck,
                                            form_data=request.form, departs=departs)
                except sqlite3.Error as e:
                    flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                    return render_template('add_info.html', funck=funck,
                                        form_data=request.form, departs=departs)
                finally:
                    conn.close()
            else:
                flash('У вас нет прав для добавления пользователя', 'danger')
                return redirect(url_for('index'))
            
    else:
        flash('Неверный параметр функции', 'danger')
        return redirect(url_for('index'))



@app.route('/edit_info', methods=['GET', 'POST'])
def edit_info():
    if 'user_id' not in session:
        flash('Необходимо авторизоваться для доступа к этой странице.', 'warning')
        return redirect(url_for('index'))

    funck = request.args.get('funck')
    match funck:
        case 'edit_users':
            if session.get('is_admin', False) or session.get('is_specialist', False):

                def get_roles():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_role, role_name FROM roles ORDER BY role_name').fetchall()
                    conn.close()
                    return [{'id': row['id_role'], 'name': row['role_name']} for row in rows]

                def get_departments():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                    conn.close()
                    return [{'id': row['id_department'], 'name': row['department_name']} for row in rows]

                # Получаем ID пользователя из аргументов
                user_id = request.args.get('user_id', type=int)
                if not user_id:
                    flash('Не указан ID пользователя', 'danger')
                    return redirect(url_for('load_table', funck='edit_users'))

                conn = get_db_connection()
                user = conn.execute('''
                    SELECT id_user, login, email, full_name, phone, aktive,
                           created_at, last_auth, kol_auth, id_role, id_department
                    FROM users WHERE id_user = ?
                ''', (user_id,)).fetchone()
                conn.close()

                if not user:
                    flash('Пользователь не найден.', 'danger')
                    return redirect(url_for('load_table', funck='edit_users'))

                # Специалист может редактировать только преподавателей (роль 4)
                if session.get('is_specialist', False) and user['id_role'] != 4:
                    flash('Вы можете редактировать только преподавателей.', 'danger')
                    return redirect(url_for('load_table', funck='edit_users'))

                # Загружаем роли и отделения только для администратора
                roles = get_roles() if session.get('is_admin', False) else None
                departments = get_departments() if session.get('is_admin', False) else None
                head_role_id = 3  # id роли "Заведующий"

                # GET – показываем форму
                if request.method == 'GET':
                    return render_template('edit_info.html',
                                           funck=funck,
                                           user=user,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id,
                                           is_admin=session.get('is_admin', False))

                # POST – обрабатываем сохранение
                full_name = request.form.get('fullName', '').strip()
                email = request.form.get('email', '').strip().lower()
                phone = request.form.get('phone', '').strip()
                aktive = 1 if request.form.get('status') == 'active' else 0
                new_password = request.form.get('password', '')
                confirm_password = request.form.get('confirmPassword', '')

                if session.get('is_admin', False):
                    role_id = request.form.get('role')
                    department_id = request.form.get('department')
                else:
                    role_id = None
                    department_id = None

                # Валидация
                errors = []
                if not full_name:
                    errors.append('ФИО обязательно')
                if not email:
                    errors.append('Email обязателен')
                elif '@' not in email or '.' not in email:
                    errors.append('Введите корректный email')
                elif len(email) > 100:
                    errors.append('Email слишком длинный')

                # Валидация пароля (если заполнен)
                if new_password or confirm_password:
                    if len(new_password) < 6:
                        errors.append('Новый пароль должен быть не менее 6 символов')
                    elif new_password != confirm_password:
                        errors.append('Пароли не совпадают')

                if session.get('is_admin', False):
                    valid_role_ids = [str(r['id']) for r in roles]
                    if not role_id or role_id not in valid_role_ids:
                        errors.append('Выберите корректную роль')
                    else:
                        if role_id == str(head_role_id):
                            if not department_id:
                                errors.append('Для заведующего необходимо выбрать отделение')
                            else:
                                valid_dept_ids = [str(d['id']) for d in departments]
                                if department_id not in valid_dept_ids:
                                    errors.append('Выбрано несуществующее отделение')
                        else:
                            department_id = None

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return render_template('edit_info.html',
                                           funck=funck,
                                           user=user,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id,
                                           is_admin=session.get('is_admin', False),
                                           form_data=request.form)

                # Проверка уникальности email (исключая текущего)
                conn = get_db_connection()
                try:
                    existing_email = conn.execute('''
                        SELECT id_user FROM users WHERE email = ? AND id_user != ?
                    ''', (email, user_id)).fetchone()
                    if existing_email:
                        flash('Пользователь с таким email уже существует', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               user=user,
                                               roles=roles,
                                               departments=departments,
                                               head_role_id=head_role_id,
                                               is_admin=session.get('is_admin', False),
                                               form_data=request.form)

                    # Формируем запрос на обновление
                    conn.execute('BEGIN TRANSACTION')
                    if session.get('is_admin', False):
                        if new_password:
                            password_hash = generate_password_hash(new_password)
                            conn.execute('''
                                UPDATE users
                                SET full_name = ?, email = ?, phone = ?, aktive = ?,
                                    id_role = ?, id_department = ?, password = ?
                                WHERE id_user = ?
                            ''', (full_name, email, phone, aktive, int(role_id), department_id, password_hash, user_id))
                        else:
                            conn.execute('''
                                UPDATE users
                                SET full_name = ?, email = ?, phone = ?, aktive = ?,
                                    id_role = ?, id_department = ?
                                WHERE id_user = ?
                            ''', (full_name, email, phone, aktive, int(role_id), department_id, user_id))
                    else:  # специалист
                        if new_password:
                            password_hash = generate_password_hash(new_password)
                            conn.execute('''
                                UPDATE users
                                SET full_name = ?, email = ?, phone = ?, aktive = ?, password = ?
                                WHERE id_user = ?
                            ''', (full_name, email, phone, aktive, password_hash, user_id))
                        else:
                            conn.execute('''
                                UPDATE users
                                SET full_name = ?, email = ?, phone = ?, aktive = ?
                                WHERE id_user = ?
                            ''', (full_name, email, phone, aktive, user_id))
                    conn.commit()
                    flash('Изменения успешно сохранены!', 'success')
                    conn.close()
                    return redirect(url_for('load_table', funck='edit_users'))

                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных: {str(e)}', 'danger')
                    conn.close()
                    return render_template('edit_info.html',
                                           funck=funck,
                                           user=user,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id,
                                           is_admin=session.get('is_admin', False),
                                           form_data=request.form)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        case 'edit_disciplines':
            if session.get('is_specialist', False):

                def get_pck_list():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_pck, name_pck FROM pck ORDER BY name_pck').fetchall()
                    conn.close()
                    return [{'id': row['id_pck'], 'name': row['name_pck']} for row in rows]

                # Получаем ID дисциплины из аргументов
                discipline_id = request.args.get('discipline_id', type=str)
                if not discipline_id:
                    flash('Не указан ID дисциплины', 'danger')
                    return redirect(url_for('load_table', funck='edit_disciplines'))

                conn = get_db_connection()
                discipline = conn.execute('''
                    SELECT d.id_discipline, d.discipline_name, d.id_pck, p.name_pck as pck_name
                    FROM disciplines d
                    LEFT JOIN pck p ON d.id_pck = p.ID_pck
                    WHERE d.id_discipline = ?
                ''', (discipline_id,)).fetchone()
                conn.close()

                if not discipline:
                    flash('Дисциплина не найдена.', 'danger')
                    return redirect(url_for('load_table', funck='edit_disciplines'))

                # Загружаем список ПЦК для всех (нужен для выбора)
                pck_list = get_pck_list()

                # GET – показываем форму
                if request.method == 'GET':
                    return render_template('edit_info.html',
                                           funck=funck,
                                           discipline=discipline,
                                           pck_list=pck_list,
                                           is_specialist=session.get('is_specialist', False))

                # POST – обрабатываем сохранение
                discipline_id_new = request.form.get('disciplineId', '').strip()
                discipline_name = request.form.get('disciplineName', '').strip()
                pck_id = request.form.get('pck', type=int)

                # Валидация
                errors = []

                # Валидация ID дисциплины
                if not discipline_id_new:
                    errors.append('ID дисциплины обязательно')
                elif not re.match(r'^[а-яА-ЯёЁ0-9.]+$', discipline_id_new):
                    errors.append('ID дисциплины может содержать только русские буквы, цифры и точки')
                elif len(discipline_id_new) > 50:
                    errors.append('ID дисциплины не может превышать 50 символов')

                # Валидация названия дисциплины
                if not discipline_name:
                    errors.append('Название дисциплины обязательно')
                elif len(discipline_name) > 50:
                    errors.append('Название дисциплины не может превышать 50 символов')

                # Валидация ПЦК
                if not pck_id:
                    errors.append('Выберите ПЦК')
                else:
                    valid_pck_ids = [str(p['id']) for p in pck_list]
                    if str(pck_id) not in valid_pck_ids:
                        errors.append('Выбрана некорректная ПЦК')

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return render_template('edit_info.html',
                                           funck=funck,
                                           discipline=discipline,
                                           pck_list=pck_list,
                                           is_specialist=session.get('is_specialist', False),
                                           form_data=request.form)

                # Проверка уникальности ID дисциплины (исключая текущую)
                conn = get_db_connection()
                try:
                    existing_discipline = conn.execute('''
                        SELECT id_discipline FROM disciplines 
                        WHERE id_discipline = ? AND id_discipline != ?
                    ''', (discipline_id_new, discipline_id)).fetchone()

                    if existing_discipline:
                        flash('Дисциплина с таким ID уже существует', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               discipline=discipline,
                                               pck_list=pck_list,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    # Проверка уникальности названия дисциплины (опционально)
                    existing_name = conn.execute('''
                        SELECT id_discipline FROM disciplines 
                        WHERE discipline_name = ? AND id_discipline != ?
                    ''', (discipline_name, discipline_id)).fetchone()

                    if existing_name:
                        flash('Дисциплина с таким названием уже существует', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               discipline=discipline,
                                               pck_list=pck_list,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    # Формируем запрос на обновление
                    conn.execute('BEGIN TRANSACTION')

                    # Проверяем, изменился ли ID дисциплины
                    if discipline_id_new != discipline_id:
                        # Если ID изменился, обновляем запись (внешние ключи с CASCADE)
                        conn.execute('''
                            UPDATE disciplines
                            SET id_discipline = ?, discipline_name = ?, id_pck = ?
                            WHERE id_discipline = ?
                        ''', (discipline_id_new, discipline_name, pck_id, discipline_id))
                    else:
                        # Простое обновление
                        conn.execute('''
                            UPDATE disciplines
                            SET discipline_name = ?, id_pck = ?
                            WHERE id_discipline = ?
                        ''', (discipline_name, pck_id, discipline_id))

                    conn.commit()
                    flash('Изменения успешно сохранены!', 'success')
                    conn.close()
                    return redirect(url_for('load_table', funck='edit_disciplines'))

                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    if 'UNIQUE constraint failed' in str(e):
                        flash('Дисциплина с таким ID или названием уже существует', 'danger')
                    else:
                        flash(f'Ошибка целостности базы данных: {str(e)}', 'danger')
                    conn.close()
                    return render_template('edit_info.html',
                                           funck=funck,
                                           discipline=discipline,
                                           pck_list=pck_list,
                                           is_specialist=session.get('is_specialist', False),
                                           form_data=request.form)
                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных: {str(e)}', 'danger')
                    conn.close()
                    return render_template('edit_info.html',
                                           funck=funck,
                                           discipline=discipline,
                                           pck_list=pck_list,
                                           is_specialist=session.get('is_specialist', False),
                                           form_data=request.form)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        case 'edit_years':
            if session.get('is_specialist', False):

                # Получаем ID учебного года из аргументов
                year_id = request.args.get('year_id', type=int)
                if not year_id:
                    flash('Не указан ID учебного года', 'danger')
                    return redirect(url_for('load_table', funck='edit_years'))

                conn = get_db_connection()
                academic_year = conn.execute('''
                    SELECT id_year, year_name
                    FROM academic_year
                    WHERE id_year = ?
                ''', (year_id,)).fetchone()
                conn.close()

                if not academic_year:
                    flash('Учебный год не найден.', 'danger')
                    return redirect(url_for('load_table', funck='edit_years'))

                # Обработка POST запроса
                if request.method == 'POST':
                    year_name = request.form.get('yearName', '').strip()

                    # Валидация
                    errors = []

                    if not year_name:
                        errors.append('Название учебного года обязательно')
                    elif len(year_name) > 50:
                        errors.append('Название учебного года не может превышать 50 символов')
                    elif not re.match(r'^\d{4}-\d{4}$', year_name):
                        errors.append('Формат должен быть: ГГГГ-ГГГГ (например, 2023-2024)')
                    else:
                        years = year_name.split('-')
                        start_year = int(years[0])
                        end_year = int(years[1])
                        if start_year >= end_year:
                            errors.append('Начальный год должен быть меньше конечного')
                        elif end_year - start_year != 1:
                            errors.append('Учебный год должен длиться 1 год (например, 2023-2024)')

                    if errors:
                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               academic_year=academic_year,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    # Проверка уникальности названия учебного года (исключая текущий)
                    conn = get_db_connection()
                    try:
                        existing_year = conn.execute('''
                            SELECT id_year FROM academic_year 
                            WHERE year_name = ? AND id_year != ?
                        ''', (year_name, year_id)).fetchone()

                        if existing_year:
                            flash('Учебный год с таким названием уже существует', 'danger')
                            conn.close()
                            return render_template('edit_info.html',
                                                   funck=funck,
                                                   academic_year=academic_year,
                                                   is_specialist=session.get('is_specialist', False),
                                                   form_data=request.form)

                        # Обновление записиlelele
                        conn.execute('BEGIN TRANSACTION')
                        conn.execute('''
                            UPDATE academic_year
                            SET year_name = ?
                            WHERE id_year = ?
                        ''', (year_name, year_id))

                        conn.commit()
                        flash('Изменения успешно сохранены!', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_years'))

                    except sqlite3.IntegrityError as e:
                        conn.rollback()
                        if 'UNIQUE constraint failed' in str(e):
                            flash('Учебный год с таким названием уже существует', 'danger')
                        else:
                            flash(f'Ошибка целостности базы данных: {str(e)}', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               academic_year=academic_year,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               academic_year=academic_year,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                # GET запрос
                return render_template('edit_info.html',
                                       funck=funck,
                                       academic_year=academic_year,
                                       is_specialist=session.get('is_specialist', False))

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        case 'edit_fgoss':
            if session.get('is_specialist', False):

                fgos_id = request.args.get('fgos_id', type=int)
                if not fgos_id:
                    flash('Не указан ID ФГОС', 'danger')
                    return redirect(url_for('load_table', funck='edit_fgoss'))

                conn = get_db_connection()
                fgos = conn.execute('''
                    SELECT id_fgos, name
                    FROM fgoss
                    WHERE id_fgos = ?
                ''', (fgos_id,)).fetchone()
                conn.close()

                if not fgos:
                    flash('ФГОС не найден.', 'danger')
                    return redirect(url_for('load_table', funck='edit_fgoss'))

                if request.method == 'POST':
                    name = request.form.get('fgosName', '').strip()

                    errors = []
                    if not name:
                        errors.append('Название ФГОС обязательно')
                    elif len(name) > 50:
                        errors.append('Название ФГОС не может превышать 50 символов')

                    if errors:
                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               fgos=fgos,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    conn = get_db_connection()
                    try:
                        conn.execute('''
                            UPDATE fgoss
                            SET name = ?
                            WHERE id_fgos = ?
                        ''', (name, fgos_id))
                        conn.commit()
                        flash('Изменения успешно сохранены!', 'success')
                        return redirect(url_for('load_table', funck='edit_fgoss'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               fgos=fgos,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)
                    finally:
                        conn.close()

                return render_template('edit_info.html',
                                       funck=funck,
                                       fgos=fgos,
                                       is_specialist=session.get('is_specialist', False))

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        case 'edit_pck':
            if session.get('is_specialist', False):

                pck_id = request.args.get('pck_id', type=int)
                if not pck_id:
                    flash('Не указан ID ПЦК', 'danger')
                    return redirect(url_for('load_table', funck='edit_pck'))

                conn = get_db_connection()
                pck = conn.execute('''
                    SELECT id_pck, name_pck
                    FROM pck
                    WHERE id_pck = ?
                ''', (pck_id,)).fetchone()
                conn.close()

                if not pck:
                    flash('ПЦК не найдена.', 'danger')
                    return redirect(url_for('load_table', funck='edit_pck'))

                if request.method == 'POST':
                    name_pck = request.form.get('pckName', '').strip()

                    errors = []
                    if not name_pck:
                        errors.append('Название ПЦК обязательно')
                    elif len(name_pck) > 50:
                        errors.append('Название ПЦК не может превышать 50 символов')

                    if errors:
                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               pck=pck,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    conn = get_db_connection()
                    try:
                        conn.execute('''
                            UPDATE pck
                            SET name_pck = ?
                            WHERE id_pck = ?
                        ''', (name_pck, pck_id))
                        conn.commit()
                        flash('Изменения успешно сохранены!', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_pck'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               pck=pck,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                return render_template('edit_info.html',
                                       funck=funck,
                                       pck=pck,
                                       is_specialist=session.get('is_specialist', False))

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

# ============================ СТУДЕНТЫ ================================ #    


# ==================== ВИДЫ ВЕДОМОСТИ ==================== #


# ==================== ГРУППЫ ==================== #


# ==================== ФОРМА ОБУЧЕНИЯ ==================== #
            

# ==================== СПЕЦИАЛЬНОСТЬ ==================== #

 
# ==================== ВЕДОМОСТЬ (С ОЦЕНКАМИ) ==================== #



if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("❌ Ошибка базы данных: База данных не найдена")
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)