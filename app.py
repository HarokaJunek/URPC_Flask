from platform import machine

from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

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
                            users.kol_auth,
                            departments.department_name
                        FROM users
                        LEFT JOIN roles ON users.id_role = roles.id_role
                        LEFT JOIN departments ON users.id_department = departments.id_department
                        WHERE users.id_user != ?
                    '''
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
                            users.kol_auth,
                            departments.department_name
                        FROM users
                        LEFT JOIN roles ON users.id_role = roles.id_role
                        LEFT JOIN departments ON users.id_department = departments.id_department
                        WHERE users.id_user != ? AND users.id_role = 4
                    '''
                    params = [session['user_id']]

                # Если передан поисковый запрос, добавляем условия фильтрации
                if search_query:
                    query += ''' AND (
                        users.full_name LIKE ? OR 
                        users.login LIKE ? OR 
                        users.email LIKE ? OR
                        departments.department_name LIKE ?
                    )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

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
            


@app.route('/delete_recording/<path:id>', methods=['POST'])
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
                    rows = conn.execute(
                        'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                    conn.close()
                    return [{'id': row['id_department'], 'name': row['department_name']} for row in rows]

                # Загружаем роли и отделения (всегда, но специалисту они не нужны)
                roles = get_roles()
                departments = get_departments()
                head_role_id = 3  # id роли "Заведующий"

                if request.method == 'GET':
                    return render_template('add_info.html',
                                           funck=funck,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id)

                # POST-обработка
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip().lower()
                password = request.form.get('password', '')
                confirm_password = request.form.get('confirmPassword', '')
                full_name = request.form.get('fullName', '').strip()
                phone = request.form.get('phone', '').strip()

                if session.get('is_admin', False):
                    role_id = request.form.get('role')
                    department_id = request.form.get('department')  # может быть None

                errors = []

                # Валидация логина
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

                # Проверка роли и отделения (только для админа)
                if session.get('is_admin', False):
                    valid_role_ids = [str(r['id']) for r in roles]
                    if not role_id or role_id not in valid_role_ids:
                        errors.append('Выберите корректную роль')
                    else:
                        # Если выбрана роль заведующего, отделение обязательно
                        if role_id == str(head_role_id):
                            if not department_id:
                                errors.append('Для заведующего необходимо выбрать отделение')
                            else:
                                valid_dept_ids = [str(d['id']) for d in departments]
                                if department_id not in valid_dept_ids:
                                    errors.append('Выбрано несуществующее отделение')
                        else:
                            department_id = None  # для других ролей отделение не сохраняется

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return render_template('add_info.html',
                                           funck=funck,
                                           form_data=request.form,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id)

                # Проверка уникальности логина и email
                conn = get_db_connection()
                try:
                    existing_user = conn.execute('SELECT id_user FROM users WHERE login = ?', (username,)).fetchone()
                    if existing_user:
                        flash('Пользователь с таким логином уже существует', 'danger')
                        return render_template('add_info.html',
                                               funck=funck,
                                               form_data=request.form,
                                               roles=roles,
                                               departments=departments,
                                               head_role_id=head_role_id)

                    existing_email = conn.execute('SELECT id_user FROM users WHERE email = ?', (email,)).fetchone()
                    if existing_email:
                        flash('Пользователь с таким email уже существует', 'danger')
                        return render_template('add_info.html',
                                               funck=funck,
                                               form_data=request.form,
                                               roles=roles,
                                               departments=departments,
                                               head_role_id=head_role_id)

                    # Хеширование пароля
                    password_hash = generate_password_hash(password)

                    # Вставка пользователя
                    conn.execute('BEGIN TRANSACTION')
                    try:
                        cursor = conn.cursor()
                        if session.get('is_admin', False):
                            cursor.execute('''
                                INSERT INTO users 
                                (login, email, password, phone, full_name, created_at, id_role, id_department)
                                VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)
                            ''', (username, email, password_hash, phone, full_name, int(role_id), department_id))
                        elif session.get('is_specialist', False):
                            # Специалист создаёт только преподавателей (id_role = 4)
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
                        return render_template('add_info.html',
                                               funck=funck,
                                               form_data=request.form,
                                               roles=roles,
                                               departments=departments,
                                               head_role_id=head_role_id)
                except sqlite3.Error as e:
                    flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                    return render_template('add_info.html',
                                           funck=funck,
                                           form_data=request.form,
                                           roles=roles,
                                           departments=departments,
                                           head_role_id=head_role_id)
                finally:
                    conn.close()

        case 'edit_disciplines':
            if session.get('is_specialist', False):
                # Вспомогательная функция для загрузки учебных планов (ПК) из БД
                def get_pck_list():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_pck, pck_name FROM pck ORDER BY pck_name').fetchall()
                    conn.close()
                    # Преобразуем в список словарей для удобства в шаблоне
                    return [{'id_pck': row['id_pck'], 'pck_name': row['pck_name']} for row in rows]

                # GET-запрос: просто показываем форму со списком учебных планов
                if request.method == 'GET':
                    pck_list = get_pck_list()
                    return render_template('add_info.html', funck=funck, pck_list=pck_list)

                # POST-запрос: обработка отправленной формы
                # 1. Получаем данные
                id_discipline = request.form.get('id_discipline', '').strip()
                discipline_name = request.form.get('discipline_name', '').strip()
                id_pck = request.form.get('id_pck', '').strip()

                # 2. Валидация
                errors = []

                # Код дисциплины
                if not id_discipline:
                    errors.append('Код дисциплины обязателен')
                elif len(id_discipline) < 2:
                    errors.append('Код дисциплины должен быть не менее 2 символов')
                elif len(id_discipline) > 50:
                    errors.append('Код дисциплины должен быть не более 50 символов')
                elif not id_discipline.replace('_', '').isalnum():
                    errors.append('Код дисциплины может содержать только буквы, цифры и подчёркивание')

                # Название дисциплины
                if not discipline_name:
                    errors.append('Название дисциплины обязательно')
                elif len(discipline_name) < 3:
                    errors.append('Название дисциплины должно быть не менее 3 символов')
                elif len(discipline_name) > 50:
                    errors.append('Название дисциплины должно быть не более 50 символов')

                # Учебный план (ПК)
                if not id_pck:
                    errors.append('Учебный план обязателен')
                else:
                    try:
                        id_pck_int = int(id_pck)
                        if id_pck_int <= 0:
                            errors.append('Выберите корректный учебный план')
                    except ValueError:
                        errors.append('Неверный формат учебного плана')

                # Если есть ошибки — показываем форму снова
                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    pck_list = get_pck_list()
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,  # передаём введённые данные для сохранения в полях
                        pck_list=pck_list
                    )

                # 3. Проверка уникальности кода дисциплины
                conn = get_db_connection()
                try:
                    existing_discipline = conn.execute(
                        'SELECT id_discipline FROM disciplines WHERE id_discipline = ?',
                        (id_discipline,)
                    ).fetchone()
                    if existing_discipline:
                        flash('Дисциплина с таким кодом уже существует', 'danger')
                        pck_list = get_pck_list()
                        return render_template('add_info.html', funck=funck,
                                               form_data=request.form, pck_list=pck_list)

                    # 4. Вставка новой дисциплины
                    conn.execute('BEGIN TRANSACTION')
                    try:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO disciplines 
                            (id_discipline, discipline_name, id_pck)
                            VALUES (?, ?, ?)
                        ''', (id_discipline, discipline_name, int(id_pck)))
                        conn.commit()
                        flash(f'Дисциплина "{discipline_name}" успешно добавлена!', 'success')

                        return redirect(url_for('load_table', funck='edit_disciplines'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных при вставке: {str(e)}', 'danger')
                        pck_list = get_pck_list()
                        return render_template('add_info.html', funck=funck,
                                               form_data=request.form, pck_list=pck_list)
                except sqlite3.Error as e:
                    flash('Ошибка подключения к базе данных. Попробуйте позже.', 'danger')
                    pck_list = get_pck_list()
                    return render_template('add_info.html', funck=funck,
                                           form_data=request.form, pck_list=pck_list)
                finally:
                    conn.close()


        # Обработка других значений funck (если есть)
        case _:
            flash('Неверный параметр функции', 'danger')
            return redirect(url_for('index'))



if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("❌ Ошибка базы данных: База данных не найдена")
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)