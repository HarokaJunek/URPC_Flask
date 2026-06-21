from platform import machine
from unittest import case
from xml.parsers.expat import errors

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import math  # Добавьте этот импорт в начало файла
import io
# import openpyxl
# from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
# from openpyxl.utils import get_column_letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
from functools import wraps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.fonts import addMapping
import io
import os

# ============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ============================================================================

app = Flask(__name__)

# Секретный ключ для подписи сессий
app.secret_key = 'your-secret-key-123-change-this'

# База будет искаться в папке instance рядом с main.py
DATABASE = os.path.join('instance', 'nagruzka_DEMO (1).db')


# ============================================================================
# 2. ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ ПРАВ
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def specialist_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_specialist', False):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def zav_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_zav', False):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def prepod_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_prepod', False):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def prepod_or_higher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (session.get('is_prepod', False) or
                session.get('is_zav', False) or
                session.get('is_specialist', False) or
                session.get('is_admin', False)):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def zav_or_higher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (session.get('is_zav', False) or
                session.get('is_specialist', False) or
                session.get('is_admin', False)):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


def specialist_or_higher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (session.get('is_specialist', False) or
                session.get('is_admin', False)):
            flash('У вас нет прав для доступа к этому разделу', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function

def generate_load_pdf(load_data, teacher_filter=None, year_filter=None, semester_filter=None):
    """
    Генерация PDF с таблицей нагрузки в альбомной ориентации
    с вертикальным текстом в заголовках и переносом в ячейках
    """
    buffer = io.BytesIO()

    # Создаем документ в альбомной ориентации с минимальными полями
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=3 * mm,
        rightMargin=3 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title="Нагрузка преподавателей"
    )

    # Регистрируем шрифт для кириллицы
    try:
        font_path = os.path.join(os.path.dirname(__file__), 'static', 'Fonts', 'DejaVuSans.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            font_name = 'DejaVu'
        else:
            font_name = 'Helvetica'
    except:
        font_name = 'Helvetica'

    styles = getSampleStyleSheet()

    # Стили
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.black,
        bold=True
    )

    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        alignment=TA_LEFT,
        spaceAfter=2,
        textColor=colors.black
    )

    # Стиль для ячеек с ПЕРЕНОСОМ текста (для ФИО, ПЦК и дисциплины)
    wrap_style = ParagraphStyle(
        'WrapStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=5,
        alignment=TA_CENTER,
        leading=5.5,
        wordWrap='CJK'
    )

    # Стиль для ЗАГОЛОВКОВ с уменьшенным межстрочным интервалом
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=4.5,
        alignment=TA_CENTER,
        leading=4.8,
        bold=True,
        wordWrap='CJK'
    )

    signature_style = ParagraphStyle(
        'SignatureStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=TA_LEFT,
        spaceAfter=2,
        textColor=colors.black
    )

    elements = []

    # Заголовок
    elements.append(Paragraph("НАГРУЗКА ПРЕПОДАВАТЕЛЯ", title_style))
    elements.append(Spacer(1, 1 * mm))

    # ========== ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО ПОЛУЧЕНИЯ ЗНАЧЕНИЙ ==========
    def safe_get(row, key, default=0):
        if row is None:
            return default
        try:
            if hasattr(row, 'keys'):
                return row[key] if key in row.keys() else default
            elif isinstance(row, dict):
                return row.get(key, default)
            else:
                return getattr(row, key, default)
        except:
            return default

    # ========== РАСЧЕТ ОБЩЕЙ НАГРУЗКИ ДЛЯ ФИЛЬТРАЦИИ ==========
    def calculate_total_load(data, teacher_name=None):
        """Расчет общей нагрузки преподавателя из данных"""
        total = 0
        for load in data:
            if teacher_name:
                load_teacher = safe_get(load, 'teacher_full_name', '')
                if load_teacher != teacher_name:
                    continue

            lectures_winter = safe_get(load, 'lectures_winter', 0) or 0
            practice_winter = safe_get(load, 'practice_winter', 0) or 0
            labs_winter = safe_get(load, 'labs_winter', 0) or 0
            seminars_winter = safe_get(load, 'seminars_winter', 0) or 0
            course_project_winter = safe_get(load, 'course_project_winter', 0) or 0

            lectures_summer = safe_get(load, 'lectures_summer', 0) or 0
            practice_summer = safe_get(load, 'practice_summer', 0) or 0
            labs_summer = safe_get(load, 'labs_summer', 0) or 0
            seminars_summer = safe_get(load, 'seminars_summer', 0) or 0
            course_project_summer = safe_get(load, 'course_project_summer', 0) or 0

            winter_with_teacher = (lectures_winter + practice_winter + labs_winter +
                                   seminars_winter + course_project_winter)
            summer_with_teacher = (lectures_summer + practice_summer + labs_summer +
                                   seminars_summer + course_project_summer)

            total += winter_with_teacher + summer_with_teacher

        return total

    # Информация о фильтрах
    info_lines = []

    if teacher_filter:
        conn = get_db_connection()
        teacher = conn.execute(
            'SELECT full_name FROM users WHERE full_name LIKE ? LIMIT 1',
            (f'%{teacher_filter}%',)
        ).fetchone()
        conn.close()
        teacher_display = teacher['full_name'] if teacher else teacher_filter

        total_hours = calculate_total_load(load_data, teacher_display)
        info_lines.append(f"Преподаватель: {teacher_display} (часов: {total_hours})")
    else:
        info_lines.append("Преподаватель: Все")
        total_hours_all = calculate_total_load(load_data)
        info_lines.append(f"Общая нагрузка всех преподавателей: {total_hours_all} часов")

    if year_filter:
        conn = get_db_connection()
        year_name = conn.execute(
            'SELECT year_name FROM academic_year WHERE id_year = ?',
            (year_filter,)
        ).fetchone()
        conn.close()

    if semester_filter:
        semester_display = 'Зимний семестр' if semester_filter == 'winter' else 'Летний семестр'
        info_lines.append(f"Семестр: {semester_display}")

    info_text = " | ".join(info_lines)
    elements.append(Paragraph(info_text, info_style))
    elements.append(Spacer(1, 2 * mm))

    # ========== ШАПКА ==========
    header_row1 = [
        '', '', '', '', '', '', '', '', '', '', '',
        '', '', '', '', '', '1 СЕМЕСТР', '', '', '', '', '',
        '', '', '', '', '', '2 СЕМЕСТР', '', '', '', '', '',
        '', '', ''
    ]

    header_row2 = [
        '№',
        'Форма',
        'Индекс',
        'Дисциплина',
        'Группа',
        'Год',
        Paragraph('Учеб.\nнед.\n(1 сем)', header_style),
        Paragraph('Учеб.\nнед.\n(2 сем)', header_style),
        'Экз',
        'Зач',
        Paragraph('Диф.\nзач', header_style),
        Paragraph('Объем ОП', header_style),
        Paragraph('Сам.', header_style),
        Paragraph('Конс.', header_style),
        Paragraph('С\nпреп.', header_style),
        Paragraph('Нагр.\nв нед.', header_style),
        Paragraph('Лекц.', header_style),
        Paragraph('Прак.\nзан.', header_style),
        Paragraph('Лаб.\nзан.', header_style),
        Paragraph('Семин.', header_style),
        Paragraph('Курс.\nпр.', header_style),
        Paragraph('Аттест.', header_style),
        Paragraph('Объем ОП', header_style),
        Paragraph('Сам.', header_style),
        Paragraph('Конс.', header_style),
        Paragraph('С\nпреп.', header_style),
        Paragraph('Нагр.\nв нед.', header_style),
        Paragraph('Лекц.', header_style),
        Paragraph('Прак.\nзан.', header_style),
        Paragraph('Лаб.\nзан.', header_style),
        Paragraph('Семин.', header_style),
        Paragraph('Курс.\nпр.', header_style),
        Paragraph('Аттест.', header_style),
        Paragraph('Нагр.\nпреп.', header_style),
        Paragraph('ФИО\nпреп.', header_style),
        Paragraph('ПЦК', header_style)
    ]

    table_data = [header_row1, header_row2]

    # Добавляем данные
    for idx, load in enumerate(load_data, 1):
        lectures_winter = safe_get(load, 'lectures_winter', 0) or 0
        practice_winter = safe_get(load, 'practice_winter', 0) or 0
        labs_winter = safe_get(load, 'labs_winter', 0) or 0
        seminars_winter = safe_get(load, 'seminars_winter', 0) or 0
        independent_winter = safe_get(load, 'independent_winter', 0) or 0
        consultations_winter = safe_get(load, 'consultations_winter', 0) or 0
        course_project_winter = safe_get(load, 'course_project_winter', 0) or 0
        attestation_winter = safe_get(load, 'attestation_winter', 0) or 0

        lectures_summer = safe_get(load, 'lectures_summer', 0) or 0
        practice_summer = safe_get(load, 'practice_summer', 0) or 0
        labs_summer = safe_get(load, 'labs_summer', 0) or 0
        seminars_summer = safe_get(load, 'seminars_summer', 0) or 0
        independent_summer = safe_get(load, 'independent_summer', 0) or 0
        consultations_summer = safe_get(load, 'consultations_summer', 0) or 0
        course_project_summer = safe_get(load, 'course_project_summer', 0) or 0
        attestation_summer = safe_get(load, 'attestation_summer', 0) or 0

        weeks_winter = safe_get(load, 'winter_week', 0) or 0
        weeks_summer = safe_get(load, 'summer_week', 0) or 0

        exam = safe_get(load, 'exam', 0) or 0
        credit = safe_get(load, 'credit', 0) or 0
        diff_credit = safe_get(load, 'diff_credit', 0) or 0

        study_form_name = safe_get(load, 'study_form_name', '') or ''
        id_discipline = safe_get(load, 'id_discipline', '') or ''
        discipline_name = safe_get(load, 'discipline_name', '') or ''
        id_group = safe_get(load, 'id_group', '') or ''
        year_name = safe_get(load, 'year_name', '') or ''
        teacher_full_name = safe_get(load, 'teacher_full_name', '') or ''
        pck_name = safe_get(load, 'pck_name', '') or ''

        # Расчеты
        winter_total_hours = (independent_winter + consultations_winter + lectures_winter +
                              practice_winter + labs_winter + seminars_winter +
                              course_project_winter + attestation_winter)
        summer_total_hours = (independent_summer + consultations_summer + lectures_summer +
                              practice_summer + labs_summer + seminars_summer +
                              course_project_summer + attestation_summer)

        winter_with_teacher = (lectures_winter + practice_winter + labs_winter +
                               seminars_winter + course_project_winter)
        summer_with_teacher = (lectures_summer + practice_summer + labs_summer +
                               seminars_summer + course_project_summer)

        # ИСПРАВЛЕННЫЙ РАСЧЕТ НАГРУЗКИ НА НЕДЕЛЮ С ОКРУГЛЕНИЕМ ВВЕРХ (ceil)
        if weeks_winter > 0 and winter_total_hours >= independent_winter:
            winter_raw = (winter_total_hours - independent_winter) / weeks_winter
            winter_weekly = math.ceil(winter_raw)  # Округление ВВЕРХ
        else:
            winter_weekly = 0

        if weeks_summer > 0 and summer_total_hours >= independent_summer:
            summer_raw = (summer_total_hours - independent_summer) / weeks_summer
            summer_weekly = math.ceil(summer_raw)  # Округление ВВЕРХ
        else:
            summer_weekly = 0

        total_teacher_load = winter_with_teacher + summer_with_teacher

        def fmt(val):
            return str(val) if val > 0 else ''

        # ========== СОЗДАЕМ ЯЧЕЙКИ С ПЕРЕНОСОМ ДЛЯ ФИО, ПЦК И ДИСЦИПЛИНЫ ==========

        # Для дисциплины - разбиваем на части, если строка длинная
        discipline_name_display = discipline_name
        if len(discipline_name_display) > 30:
            parts = discipline_name_display.split(' ')
            if len(parts) > 1:
                lines = []
                current_line = ''
                for part in parts:
                    if len(current_line) + len(part) + 1 <= 25:
                        if current_line:
                            current_line += ' ' + part
                        else:
                            current_line = part
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = part
                if current_line:
                    lines.append(current_line)
                discipline_name_display = '\n'.join(lines)
            else:
                discipline_name_display = '\n'.join(
                    [discipline_name_display[i:i + 20] for i in range(0, len(discipline_name_display), 20)])

        # Для ФИО - разбиваем на части, если строка длинная
        teacher_name = teacher_full_name
        if len(teacher_name) > 20:
            parts = teacher_name.split(' ')
            if len(parts) >= 3:
                teacher_name = '\n'.join(parts)
            elif len(parts) == 2:
                teacher_name = '\n'.join(parts)
            else:
                teacher_name = '\n'.join([teacher_name[i:i + 10] for i in range(0, len(teacher_name), 10)])

        # Для ПЦК - тоже разбиваем, если длинное
        pck_name_display = pck_name
        if len(pck_name_display) > 15:
            parts = pck_name_display.split(' ')
            if len(parts) > 1:
                pck_name_display = '\n'.join(parts)
            else:
                pck_name_display = '\n'.join([pck_name_display[i:i + 10] for i in range(0, len(pck_name_display), 10)])

        row = [
            str(idx),
            study_form_name,
            str(id_discipline),
            Paragraph(discipline_name_display, wrap_style),
            id_group,
            year_name,
            fmt(weeks_winter),
            fmt(weeks_summer),
            fmt(exam),
            fmt(credit),
            fmt(diff_credit),
            # 1 семестр
            fmt(winter_total_hours),
            fmt(independent_winter),
            fmt(consultations_winter),
            fmt(winter_with_teacher),
            fmt(winter_weekly),  # <-- ЗДЕСЬ БУДЕТ НАГРУЗКА НА НЕДЕЛЮ 1 СЕМ
            fmt(lectures_winter),
            fmt(practice_winter),
            fmt(labs_winter),
            fmt(seminars_winter),
            fmt(course_project_winter),
            fmt(attestation_winter),
            # 2 семестр
            fmt(summer_total_hours),
            fmt(independent_summer),
            fmt(consultations_summer),
            fmt(summer_with_teacher),
            fmt(summer_weekly),  # <-- ЗДЕСЬ БУДЕТ НАГРУЗКА НА НЕДЕЛЮ 2 СЕМ
            fmt(lectures_summer),
            fmt(practice_summer),
            fmt(labs_summer),
            fmt(seminars_summer),
            fmt(course_project_summer),
            fmt(attestation_summer),
            fmt(total_teacher_load),
            Paragraph(teacher_name, wrap_style),
            Paragraph(pck_name_display, wrap_style),
        ]
        table_data.append(row)

    # ========== ШИРИНА КОЛОНОК ==========
    col_widths = [
        4.5 * mm,  # 0: №
        9 * mm,  # 1: Форма
        11 * mm,  # 2: Индекс
        20 * mm,  # 3: Дисциплина
        13 * mm,  # 4: Группа
        10 * mm,  # 5: Год
        10 * mm,  # 6: Нед.1
        10 * mm,  # 7: Нед.2
        4.5 * mm,  # 8: Экз
        4.5 * mm,  # 9: Зач
        5.5 * mm,  # 10: Д.Зач
        # 1 семестр (11 колонок)
        7 * mm,  # 11: ОП
        5 * mm,  # 12: Сам.
        5 * mm,  # 13: Конс.
        7 * mm,  # 14: С преп.
        7 * mm,  # 15: Нагр. в нед.
        5 * mm,  # 16: Лекции
        6 * mm,  # 17: Пр.зан.
        6 * mm,  # 18: Лаб.зан.
        7 * mm,  # 19: Семин.
        6 * mm,  # 20: Курс.пр.
        8 * mm,  # 21: Аттест.
        # 2 семестр (11 колонок)
        7 * mm,  # 22: ОП
        5 * mm,  # 23: Сам.
        5 * mm,  # 24: Конс.
        7 * mm,  # 25: С преп.
        7 * mm,  # 26: Нагр. в нед.
        5.5 * mm,  # 27: Лекции
        6 * mm,  # 28: Пр.зан.
        6 * mm,  # 29: Лаб.зан.
        7 * mm,  # 30: Семин.
        6 * mm,  # 31: Курс.пр.
        8 * mm,  # 32: Аттест.
        8 * mm,  # 33: Нагр.
        20 * mm,  # 34: ФИО
        16 * mm,  # 35: ПЦК
    ]

    # Создаем таблицу
    table = Table(table_data, colWidths=col_widths, repeatRows=2)

    # ========== ОБЪЕДИНЕНИЕ ЯЧЕЕК ==========
    table._span = [(11, 0, 21, 0)]  # 1 СЕМЕСТР
    table._span.append((22, 0, 32, 0))  # 2 СЕМЕСТР

    # ========== СТИЛИ ==========
    style = TableStyle([
        # Верхняя строка - черный фон
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 6.5),
        ('BOLD', (0, 0), (-1, 0), True),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),

        # Нижняя строка - серый фон
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
        ('FONTNAME', (0, 1), (-1, 1), font_name),
        ('FONTSIZE', (0, 1), (-1, 1), 4.5),
        ('BOLD', (0, 1), (-1, 1), True),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),

        # Данные
        ('FONTNAME', (0, 2), (-1, -1), font_name),
        ('FONTSIZE', (0, 2), (-1, -1), 4.5),
        ('ALIGN', (0, 2), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 2), (-1, -1), 'MIDDLE'),

        # Сетка
        ('GRID', (0, 0), (-1, -1), 0.2, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),

        # Отступы
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),

        # Разделители семестров
        ('LINEAFTER', (10, 0), (10, -1), 1.0, colors.black),
        ('LINEAFTER', (21, 0), (21, -1), 1.0, colors.black),
    ])

    # ========== ВЕРТИКАЛЬНЫЙ ТЕКСТ ==========
    for col in range(6, 36):
        try:
            style.add('ROTATION', (col, 1), (col, 1), 90)
        except:
            pass

    table.setStyle(style)
    elements.append(table)

    # Подпись
    elements.append(Spacer(1, 6 * mm))

    if teacher_filter:
        conn = get_db_connection()
        teacher = conn.execute(
            'SELECT full_name FROM users WHERE full_name LIKE ? LIMIT 1',
            (f'%{teacher_filter}%',)
        ).fetchone()
        conn.close()
        signature_name = teacher['full_name'] if teacher else teacher_filter
    else:
        signature_name = "_____________________"

    elements.append(Paragraph(
        f'<b>{signature_name}</b> ознакомлен(а) с нагрузкой _________________',
        signature_style
    ))
    elements.append(Spacer(1, 1.5 * mm))

    elements.append(Paragraph(
        f'<b>Дата:</b> _______________',
        signature_style
    ))

    # Строим PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Ведомости (экспорт в pdf)
def export_statement_pdf(id_statement):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    conn = get_db_connection()
    
    # Данные ведомости (шапка)
    statement = conn.execute('''
        SELECT 
            statements.id_statement,
            specialties.id_specialty,
            specialties.specialty_name,
            academic_year.year_name,
            groups.course_number,
            workload.id_group,
            statements.semester,
            disciplines.discipline_name,
            users.full_name,
            statements.excused,
            statements.unexcused,
            statements.filled_at,
            departments.department_name
        FROM statements
        LEFT JOIN workload ON statements.id_discipline = workload.id_load
        LEFT JOIN academic_year ON workload.id_year = academic_year.id_year
        LEFT JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
        LEFT JOIN groups ON workload.id_group = groups.id_group 
        LEFT JOIN users ON workload.id_teacher = users.id_user
        LEFT JOIN specialties ON groups.id_specialty = specialties.id_specialty
        LEFT JOIN departments ON specialties.id_department = departments.id_department
        WHERE statements.id_statement = ?
    ''', (id_statement,)).fetchone()
    
    # Список студентов с оценками
    students = conn.execute('''
        SELECT 
            students.full_name,
            students.id_student,
            grades.grade
        FROM students
        LEFT JOIN grades ON students.id_student = grades.id_student 
            AND grades.id_statement = ?
        WHERE students.id_group = ?
    ''', (id_statement, statement['id_group'])).fetchall()
    
    conn.close()
    
    # Считаем статистику
    grade_A = grade_B = grade_C = grade_D = not_been = 0
    for s in students:
        g = s['grade']
        if g == 5: grade_A += 1
        elif g == 4: grade_B += 1
        elif g == 3: grade_C += 1
        elif g == 2: grade_D += 1
        elif g == 0: not_been += 1
    grades_all = grade_A + grade_B + grade_C + grade_D
    
    def format_date(date_str):
        if not date_str:
            return 'Не указана'
        try:
            y, m, d = date_str.split('-')
            months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            return f"«{int(d):02d}» {months[int(m)-1]} {y}г."
        except:
            return date_str

    # Создаём PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Arial", 14)
    
    # ЗАГОЛОВОК 
    c.setFont("Arial", 10)
    y = height - 30
    c.drawCentredString(width/2, y, "Государственное автономное профессиональное образовательное учреждение Свердловской области")
    y -= 15
    c.drawCentredString(width/2, y, "«Уральский политехнический колледж - Межрегиональный центр компетенций»")
    y -= 25
    c.setFont("Arial", 16)
    c.drawCentredString(width/2, y, f"{statement['department_name']} отделение")
    y -= 20
    c.drawCentredString(width/2, y, "Оценочная ведомость")
    
    # ШАПКА 
    c.setFont("Arial", 12)
    y -= 20
    left_margin = 40
    right_margin = width - 40
    
    c.setFont("Arial-Bold", 12)
    c.drawString(left_margin, y, "Специальность: ")
    c.setFont("Arial", 12)
    c.drawString(left_margin + 100, y, statement['id_specialty'] + " " +statement['specialty_name'] or '')
    y -= 20

    c.setFont("Arial-Bold", 12)
    c.drawString(left_margin, y, "Учебный год: ")
    c.setFont("Arial", 12)
    c.drawString(left_margin + 100, y, statement['year_name'] or '')
    c.setFont("Arial-Bold", 12)
    c.drawString(width/2, y, "Курс: ")  # начинается с середины
    c.setFont("Arial", 12)
    c.drawString(width/2 + 40, y, str(statement['course_number'] or ''))
    y -= 20

    c.setFont("Arial-Bold", 12)
    c.drawString(left_margin, y, "Группа: ")
    c.setFont("Arial", 12)
    c.drawString(left_margin + 100, y, statement['id_group'] or '')
    c.setFont("Arial-Bold", 12)
    c.drawString(width/2, y, "Семестр: ")  # начинается с середины
    c.setFont("Arial", 12)
    c.drawString(width/2 + 70, y, str(statement['semester'] or ''))
    y -= 20

    c.setFont("Arial-Bold", 12)
    c.drawString(left_margin, y, "Дисциплина: ")
    c.setFont("Arial", 12)
    c.drawString(left_margin + 100, y, statement['discipline_name'] or '')
    y -= 20

    c.setFont("Arial-Bold", 12)
    c.drawString(left_margin, y, "Зачет принял: ")
    c.setFont("Arial", 12)
    c.drawString(left_margin + 100, y, statement['full_name'] or '')
    
    # ТАБЛИЦА
    y -= 25
    table_data = [["№", "ФИО студента", "Оценка"]]  # заголовки
    for idx, student in enumerate(students, 1):
        grade = student['grade']
        grade_display = 'Н/Я' if grade == 0 else (str(grade) if grade else '')
        table_data.append([str(idx), student['full_name'], grade_display])

    main_table = Table(table_data, colWidths=[100, 270, 130])

    main_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    main_table.wrapOn(c, width - 2 * left_margin, height - y)
    main_table.drawOn(c, left_margin, y - len(table_data) * 16)
    
    # СВОДНАЯ СТАТИСТИКА
    y -= len(table_data) * 16 + 10   # сдвигаем ниже таблицы
    stats_data = [
        ["Не явилось", str(not_been), "Получено оценок", str(grades_all)],
        ["По уважительной причине", str(statement['excused'] or 0),"Неудовлетворительно", str(grade_D) ],
        ["По неуважительной причине", str(statement['unexcused'] or 0), "Удовлетворительно", str(grade_C)],
        ["", "", "Хорошо", str(grade_B)],
        ["", "", "Отлично", str(grade_A)],
    ]

    stats_table = Table(stats_data, colWidths=[200, 60, 220, 30])

    stats_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    stats_table.wrapOn(c, width - 2 * left_margin, height - y)
    stats_table.drawOn(c, left_margin, y - len(stats_data) * 18)
    
    y -= len(stats_data) * 18 + 20  # сдвигаем ниже таблицы
    c.drawString(left_margin,y, f"Дата сдачи: {format_date(statement['filled_at'])}")
    c.drawString(width/2 + 8,  y, "Преподаватель: ____________________")    
    c.save()
    buffer.seek(0)
    print("PDF сгенерирован, размер:", len(buffer.getvalue()), "байт")
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'statement_{id_statement}.pdf')

# Успеваемость (экспорт в pdf)
def export_report_pdf(group_filter, semester_filter, is_diploma=''):
    conn = get_db_connection()
    
    query = '''
        SELECT 
            students.id_student,
            students.full_name, 
            grades.grade,
            disciplines.discipline_name, 
            workload.id_group, 
            statements.semester,
            statement_types.type_name
        FROM students
        INNER JOIN grades ON students.id_student = grades.id_student
        INNER JOIN statements ON grades.id_statement = statements.id_statement
        INNER JOIN statement_types ON statements.id_type = statement_types.id_type
        INNER JOIN workload ON statements.id_discipline = workload.id_load
        INNER JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
        WHERE workload.id_group = ?
        AND statements.semester = ?
    '''
    params = [group_filter, semester_filter]
    if is_diploma:
        query += ' AND statements.is_diploma = 1'
    
    table_info = conn.execute(query, params).fetchall()
    conn.close()
    
    # Подготавливаем control_types для сложной шапки
    control_types_dict = {}
    for row in table_info:
        type_name = row['type_name'] or 'Без типа'
        disc_name = row['discipline_name']
        if type_name not in control_types_dict:
            control_types_dict[type_name] = []
        # Проверяем, нет ли уже такой дисциплины в этом типе
        if disc_name not in [d['name'] for d in control_types_dict[type_name]]:
            control_types_dict[type_name].append({
                'id': disc_name,
                'name': disc_name,
                'avg_grade': 0
            })

    # Преобразуем в список для шаблона
    control_types = []
    total_cols = 0
    for type_name, discs in control_types_dict.items():
        control_types.append({
            'name': type_name,
            'disciplines': discs
        })
        total_cols += len(discs)

    # Группируем оценки по студентам
    students_dict = {}
    for row in table_info:
        sid = row['id_student']
        if sid not in students_dict:
            students_dict[sid] = {
                'full_name': row['full_name'],
                'grades': {}
            }
        students_dict[sid]['grades'][row['discipline_name']] = row['grade']

    # Считаем средний балл для каждого студента
    students = []
    for sid, s_data in students_dict.items():
        grades_list = [g if g != 0 else 1 for g in s_data['grades'].values() if g is not None]
        avg = round(sum(grades_list) / len(grades_list), 2) if grades_list else 0
        s_data['avg_grade'] = avg
        students.append(s_data)

    # Считаем средний балл по каждой дисциплине
    for type_item in control_types:
        for disc in type_item['disciplines']:
            all_grades = []
            for student in students:
                grade = student['grades'].get(disc['id'], None)
                if grade is not None:
                    if grade == 0:
                        all_grades.append(1)
                    elif grade > 0:
                        all_grades.append(grade)
            disc['avg_grade'] = round(sum(all_grades) / len(all_grades), 2) if all_grades else 0
                
    # Создаём PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Заголовок
    title = "Приложение к диплому" if is_diploma else "Итоговая успеваемость"
    c.setFont("Arial", 16)
    c.drawCentredString(width/2, height - 30, title)
    c.drawCentredString(width/2, height - 50, f"Группа: {group_filter}, Семестр: {semester_filter}")

    table_data = []

    # Первая строка шапки: пустые ячейки + типы контроля
    header1 = ["", ""]
    for type_item in control_types:
        header1.append(type_item['name'] or '—')
        # Добавляем пустые ячейки для остальных колонок этого типа
        for _ in range(len(type_item['disciplines']) - 1):
            header1.append("")
    header1.append("")
    table_data.append(header1)

    # Вторая строка: №, ФИО, названия дисциплин
    header2 = ["№", "ФИО студента"]
    for type_item in control_types:
        for disc in type_item['disciplines']:
            header2.append(disc['name'] or '—')
    header2.append("")
    table_data.append(header2)

    # Третья строка: средний балл по дисциплине
    header3 = ["Ср. балл", "по дисциплине"]
    for type_item in control_types:
        for disc in type_item['disciplines']:
            header3.append(str(disc['avg_grade']))
    header3.append("Ср. балл студента")
    table_data.append(header3)

    # Данные студентов
    for idx, student in enumerate(students, 1):
        row = [str(idx), student['full_name']]
        for type_item in control_types:
            for disc in type_item['disciplines']:
                grade = student['grades'].get(disc['id'], '—')
                row.append(str(grade) if grade is not None else '—')
        row.append(str(student['avg_grade']))
        table_data.append(row)

    # Создаём таблицу
    total_cols = len(header2)
    col_widths = [30, 120] + [50] * (total_cols - 2)
    table = Table(table_data, colWidths=col_widths)

    # Стиль
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arial'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (1, 0)),  # объединяем "Ср. балл" и "по дисциплине"
    ]))

    table.wrapOn(c, width - 40, height - 80)
    table.drawOn(c, 20, height - 80 - len(table_data) * 16)
    
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'report_{group_filter}_{semester_filter}.pdf')

# ============================================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД
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
# 4. МАРШРУТЫ
# ============================================================================
@app.route('/export_pdf_nagruzka', methods=['GET'])
def export_pdf_nagruzka():
    """Экспорт нагрузки в PDF с учетом фильтров"""
    if not session.get('is_specialist', False) or session.get('is_prepod', False):
        flash('У вас нет прав доступа к этому разделу.', 'danger')
        return redirect(url_for('index'))

    try:
        # Получаем параметры фильтров
        search_query = request.args.get('search', '')
        year_filter = request.args.get('year')
        teacher_filter = request.args.get('teacher')
        group_filter = request.args.get('group')
        discipline_filter = request.args.get('discipline')
        fgos_filter = request.args.get('fgos')
        semester_filter = request.args.get('semester')

        # Формируем запрос как в edit_nagruzka
        conn = get_db_connection()

        query = '''
            SELECT 
                w.*,
                ay.winter_week,
                ay.summer_week,
                ay.year_name,
                u.full_name as teacher_full_name,
                d.discipline_name,
                g.id_group,
                f.name as fgos_name,
                p.name_pck as pck_name,
                sf.form_name as study_form_name
            FROM workload w
            LEFT JOIN academic_year ay ON w.id_year = ay.id_year
            LEFT JOIN users u ON w.id_teacher = u.id_user
            LEFT JOIN disciplines d ON w.id_discipline = d.id_discipline
            LEFT JOIN groups g ON w.id_group = g.id_group
            LEFT JOIN fgoss f ON w.id_fgos = f.id_fgos
            LEFT JOIN pck p ON d.id_pck = p.id_pck
            LEFT JOIN study_form sf ON g.id_study_form = sf.id_form
            WHERE 1=1
        '''
        params = []

        # Поиск
        if search_query:
            query += ''' AND (
                ay.year_name LIKE ? OR 
                u.full_name LIKE ? OR 
                d.discipline_name LIKE ? OR 
                g.id_group LIKE ? OR 
                f.name LIKE ? OR
                w.id_load LIKE ?
            )'''
            like_pattern = f'%{search_query}%'
            params.extend([like_pattern] * 6)

        # Фильтры
        if year_filter and year_filter != '':
            query += ' AND w.id_year = ?'
            params.append(year_filter)

        if teacher_filter and teacher_filter != '':
            query += ' AND u.full_name LIKE ?'
            params.append(f'%{teacher_filter}%')

        if group_filter and group_filter != '':
            query += ' AND w.id_group = ?'
            params.append(group_filter)

        if discipline_filter and discipline_filter != '':
            query += ' AND d.discipline_name LIKE ?'
            params.append(f'%{discipline_filter}%')

        if fgos_filter and fgos_filter != '':
            query += ' AND w.id_fgos = ?'
            params.append(fgos_filter)

        # Выполняем запрос
        cursor = conn.execute(query, params)
        table_info = cursor.fetchall()

        # Фильтр по семестру
        if semester_filter:
            filtered_info = []
            for load in table_info:
                show = True
                if semester_filter == 'winter' and (
                        load['lectures_winter'] == 0 and load['practice_winter'] == 0 and
                        load['labs_winter'] == 0 and load['seminars_winter'] == 0 and
                        load['course_project_winter'] == 0):
                    show = False
                if semester_filter == 'summer' and (
                        load['lectures_summer'] == 0 and load['practice_summer'] == 0 and
                        load['labs_summer'] == 0 and load['seminars_summer'] == 0 and
                        load['course_project_summer'] == 0):
                    show = False
                if show:
                    filtered_info.append(load)
            table_info = filtered_info

        conn.close()

        # Проверяем наличие данных
        if not table_info:
            flash('Нет данных для экспорта в PDF', 'warning')
            return redirect(url_for('load_table', funck='edit_nagruzka', **request.args))

        # Генерируем PDF
        pdf_buffer = generate_load_pdf(
            table_info,
            teacher_filter,
            year_filter,
            semester_filter
        )

        # Формируем имя файла
        filename = f'Нагрузка_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        flash(f'Ошибка при генерации PDF: {str(e)}', 'danger')
        return redirect(url_for('load_table', funck='edit_nagruzka', **request.args))

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

@app.route('/', methods=['GET', 'POST'])
def index():
    # ============================================
    # ОБРАБОТКА POST-ЗАПРОСА (отправка формы)
    # ============================================
    if request.method == 'POST':
        # 1. ПОЛУЧАЕМ ДАННЫЕ ИЗ ФОРМЫ
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

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
                # if user['is_admin']:
                print("🚀 Перенаправление в админ-панель")
                return redirect(url_for('admin_dashboard'))
            # else:

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
        # НАГРУЗКА!!!!!!!!!!!!

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
                table_info = cursor.fetchall()
                conn.close()

                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        case 'edit_nagruzka':
            if session.get('is_specialist', False) or session.get('is_prepod', False):
                conn = get_db_connection()

                # Получение списков для фильтров
                academic_years = conn.execute(
                    'SELECT id_year, year_name, winter_week, summer_week FROM academic_year ORDER BY year_name').fetchall()
                groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()

                # Получаем параметры из URL
                search_query = request.args.get('search', '')
                year_filter = request.args.get('year')
                teacher_filter = request.args.get('teacher')
                group_filter = request.args.get('group')
                discipline_filter = request.args.get('discipline')
                fgos_filter = request.args.get('fgos')
                semester_filter = request.args.get('semester')

                # Базовый запрос с JOIN
                query = '''
                    SELECT 
                        w.*,
                        ay.winter_week,
                        ay.summer_week,
                        ay.year_name,
                        u.full_name as teacher_full_name,
                        d.discipline_name,
                        g.id_group,
                        f.name as fgos_name,
                        p.name_pck as pck_name,
                        sf.form_name as study_form_name
                    FROM workload w
                    LEFT JOIN academic_year ay ON w.id_year = ay.id_year
                    LEFT JOIN users u ON w.id_teacher = u.id_user
                    LEFT JOIN disciplines d ON w.id_discipline = d.id_discipline
                    LEFT JOIN groups g ON w.id_group = g.id_group
                    LEFT JOIN fgoss f ON w.id_fgos = f.id_fgos
                    LEFT JOIN pck p ON d.id_pck = p.id_pck
                    LEFT JOIN study_form sf ON g.id_study_form = sf.id_form
                    WHERE 1=1
                '''
                params = []

                if session.get('is_prepod', False) and not session.get('is_specialist', False):
                    query += ' AND w.id_teacher = ?'
                    params.append(session['user_id'])

                # Добавляем условия для ПОИСКА
                if search_query:
                    query += ''' AND (
                        ay.year_name LIKE ? OR 
                        u.full_name LIKE ? OR 
                        d.discipline_name LIKE ? OR 
                        g.id_group LIKE ? OR 
                        f.name LIKE ? OR
                        w.id_load LIKE ?
                    )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern] * 6)

                # Добавляем условия для ФИЛЬТРОВ (в SQL, а не в Python)
                if year_filter and year_filter != '':
                    query += ' AND w.id_year = ?'
                    params.append(year_filter)

                if teacher_filter and teacher_filter != '':
                    query += ' AND u.full_name LIKE ?'
                    params.append(f'%{teacher_filter}%')

                if group_filter and group_filter != '':
                    query += ' AND w.id_group = ?'
                    params.append(group_filter)

                if discipline_filter and discipline_filter != '':
                    query += ' AND d.discipline_name LIKE ?'
                    params.append(f'%{discipline_filter}%')

                if fgos_filter and fgos_filter != '':
                    query += ' AND w.id_fgos = ?'
                    params.append(fgos_filter)

                # Выполняем запрос
                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()

                # Применяем фильтр по семестру (его сложнее сделать в SQL, оставляем в Python)
                if semester_filter:
                    filtered_info = []
                    for load in table_info:
                        show = True
                        if semester_filter == 'winter' and (
                                load['lectures_winter'] == 0 and load['practice_winter'] == 0 and
                                load['labs_winter'] == 0 and load['seminars_winter'] == 0 and
                                load['course_project_winter'] == 0):
                            show = False
                        if semester_filter == 'summer' and (
                                load['lectures_summer'] == 0 and load['practice_summer'] == 0 and
                                load['labs_summer'] == 0 and load['seminars_summer'] == 0 and
                                load['course_project_summer'] == 0):
                            show = False
                        if show:
                            filtered_info.append(load)
                    table_info = filtered_info

                conn.close()

                return render_template('load_table.html',
                                       funck=funck,
                                       table_info=table_info,
                                       academic_years=academic_years,
                                       groups=groups,
                                       search_query=search_query,
                                       year_filter=year_filter,
                                       teacher_filter=teacher_filter,
                                       group_filter=group_filter,
                                       discipline_filter=discipline_filter,
                                       fgos_filter=fgos_filter,
                                       semester_filter=semester_filter)
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

        case 'edit_otdel':
            if session.get('is_admin', False):
                conn = get_db_connection()

                # Базовый запрос
                query = 'SELECT * FROM departments'
                params = []

                # Если передан поисковый запрос, добавляем WHERE с условиями
                if search_query:
                    query += ' WHERE departments.id_department LIKE ? OR departments.department_name LIKE ?'
                    like_pattern = f'%{search_query}%'
                    params = [like_pattern, like_pattern]

                cursor = conn.execute(query, params)
                table_info = cursor.fetchall()  # Получаем все результаты в виде списка
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

        # СТУДЕНТЫ
        case 'edit_students':
            if (session.get('is_zav', False)):
                conn = get_db_connection()
                query = '''
                    SELECT 
                        students.id_student,
                        students.full_name,
                        groups.id_group
                    FROM students
                    INNER JOIN groups ON groups.id_group = students.id_group
                    '''
                params = []
                if search_query:
                    query += ''' AND (
                        students.id_student LIKE ? OR
                        students.full_name LIKE ? OR
                        groups.id_group LIKE ? 
                        )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern])
                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html', table_info=table_info, funck=funck)

            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # ТИП ВЕДОМОСТИ
        case 'edit_typesved':
            if (session.get('is_zav', False)):
                conn = get_db_connection()
                query = '''
                    SELECT 
                        statement_types.id_type,
                        statement_types.type_name
                    FROM statement_types
                    '''
                params = []
                if search_query:
                    query += ''' AND (
                        statement_types.id_type LIKE ? OR
                        statement_types.type_name LIKE ? 
                        )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern])
                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # ГРУППЫ
        case 'edit_groups':
            if (session.get('is_specialist', False) or session.get('is_zav', False)):
                conn = get_db_connection()
                query = ('SELECT groups.id_group, groups.course_number, study_form.form_name, '
                         'users.id_user as class_teacher_id, users.full_name as teacher_name, '
                         'specialties.id_specialty as specialty_name '
                         'FROM groups '
                         'INNER JOIN users ON groups.id_class_teacher = users.id_user '
                         'INNER JOIN specialties ON groups.id_specialty = specialties.id_specialty '
                         'INNER JOIN study_form ON groups.id_study_form = study_form.id_form')
                params = []
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

        # ФОРМЫ ОБУЧЕНИЯ
        case 'edit_formobuch':
            if (session.get('is_zav', False)):
                conn = get_db_connection()
                query = '''
                    SELECT 
                        study_form.id_form,
                        study_form.form_name
                    FROM study_form
                    '''
                params = []
                if search_query:
                    query += ''' AND (
                        study_form.id_form LIKE ? OR
                        study_form.form_name LIKE ? 
                        )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern])
                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # СПЕЦИАЛЬНОСТИ
        case 'edit_spec':
            if (session.get('is_zav', False)):
                conn = get_db_connection()
                query = '''
                    SELECT 
                        specialties.id_specialty,
                        specialties.specialty_name,
                        specialties.id_department,
                        departments.department_name
                    FROM specialties
                    INNER JOIN departments ON specialties.id_department = departments.id_department
                    '''
                params = []
                if search_query:
                    query += ''' WHERE (
                        specialties.id_specialty LIKE ? OR
                        specialties.specialty_name LIKE ? OR
                        departments.department_name LIKE ?
                        )'''
                    like_pattern = f'%{search_query}%'
                    params.extend([like_pattern, like_pattern, like_pattern])
                query += ' ORDER BY specialties.id_specialty'
                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html', table_info=table_info, funck=funck)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # ВЕДОМОСТЬ
        case 'edit_statement':
            if (session.get('is_zav', False) or session.get('is_prepod', False)):

                id_statement = request.args.get('id_statement')
                if request.args.get('action') == 'unsubmit':
                    conn = get_db_connection()
                    print("DEBUG: unsubmit triggered, id_statement =", request.args.get('id_statement'))
                    conn.execute('UPDATE statements SET status = 0 WHERE id_statement = ?', (id_statement,))
                    conn.commit()
                    flash('Сдача ведомости отменена!', 'success')
                    conn.close()
                    return redirect(url_for('load_table', funck='edit_statement',))
                
                status = request.args.get('status', '')
                conn = get_db_connection()
                query = '''
                    SELECT 
                        statements.id_statement, 
                        users.full_name,
                        disciplines.discipline_name, 
                        workload.id_group, 
                        statements.semester, 
                        statements.status
                    FROM statements

                    INNER JOIN workload ON statements.id_discipline = workload.id_load
                    INNER JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
                    INNER JOIN users ON workload.id_teacher = users.id_user
                    where 1=1
                    '''
                params = []

                if session.get('is_prepod', False) and not session.get('is_zav', False):
                    query += ' and workload.id_teacher = ?'
                    params.append(session['user_id']) 
                
                # Фильтрация по статусу
                status_filter = request.args.get('status', '')
                if status_filter:
                    query += ' and statements.status = ?'
                    params.append(status_filter)
                elif search_query:
                    query += ' and (users.full_name LIKE ? OR disciplines.discipline_name LIKE ? OR workload.id_group LIKE ?)'
                    like_pattern = '%' + search_query + '%'
                    params.extend([like_pattern, like_pattern, like_pattern])

                # Добавляем сортировку
                query += ' ORDER BY users.full_name ASC, disciplines.discipline_name ASC'

                # Получаем данные для фильтров
                groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                    
                table_info = conn.execute(query, params).fetchall()
                conn.close()
                return render_template('load_table.html',
                                       status = status,
                                       table_info=table_info,
                                       funck=funck,
                                       groups=groups,
                                       session=session)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # УСПЕВАЕМОСТЬ
        case 'edit_report':
            if (session.get('is_zav', False)):
                group_filter = request.args.get('group', '')
                semester_filter = request.args.get('semester', '')
                is_diploma = request.args.get('is_diploma', '')
                if request.args.get('export') == 'pdf':
                     return export_report_pdf(group_filter, semester_filter, is_diploma)
                table_info = []

                conn = get_db_connection()
                groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                if group_filter and semester_filter:
                    query = '''
                        SELECT 
                            students.id_student,
                            students.full_name, 
                            grades.grade,
                            disciplines.discipline_name, 
                            workload.id_group, 
                            statements.semester,
                            statement_types.type_name
                        FROM students
                        INNER JOIN grades ON students.id_student = grades.id_student
                        INNER JOIN statements ON grades.id_statement = statements.id_statement
                        INNER JOIN statement_types ON statements.id_type = statement_types.id_type
                        INNER JOIN workload ON statements.id_discipline = workload.id_load
                        INNER JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
                        WHERE workload.id_group = ?
                        AND statements.semester = ?
                    '''
                    params = [group_filter, semester_filter]

                    if is_diploma:
                        query += ' AND statements.is_diploma = 1'

                    table_info = conn.execute(query, params).fetchall()
                else:
                    table_info = []

                # Подготавливаем control_types для сложной шапки
                control_types_dict = {}
                for row in table_info:
                    type_name = row['type_name'] or 'Без типа'
                    disc_name = row['discipline_name']

                    if type_name not in control_types_dict:
                        control_types_dict[type_name] = []

                    # Проверяем, нет ли уже такой дисциплины в этом типе
                    if disc_name not in [d['name'] for d in control_types_dict[type_name]]:
                        control_types_dict[type_name].append({
                            'id': disc_name,
                            'name': disc_name,
                            'avg_grade': 0
                        })

                # Преобразуем в список для шаблона
                control_types = []
                total_cols = 0
                for type_name, discs in control_types_dict.items():
                    control_types.append({
                        'name': type_name,
                        'disciplines': discs
                    })
                    total_cols += len(discs)

                # Группируем оценки по студентам
                students_dict = {}
                for row in table_info:
                    sid = row['id_student']
                    if sid not in students_dict:
                        students_dict[sid] = {
                            'full_name': row['full_name'],
                            'grades': {}
                        }
                    students_dict[sid]['grades'][row['discipline_name']] = row['grade']

                # Считаем средний балл для каждого студента
                students = []
                for sid, s_data in students_dict.items():
                    grades_list = [g if g != 0 else 1 for g in s_data['grades'].values() if g is not None]
                    avg = round(sum(grades_list) / len(grades_list), 2) if grades_list else 0
                    s_data['avg_grade'] = avg
                    students.append(s_data)

                # Считаем средний балл по каждой дисциплине
                for type_item in control_types:
                    for disc in type_item['disciplines']:
                        all_grades = []
                        for student in students:
                            grade = student['grades'].get(disc['id'], None)
                            if grade is not None:
                                if grade == 0:
                                    all_grades.append(1)
                                elif grade > 0:
                                    all_grades.append(grade)
                        disc['avg_grade'] = round(sum(all_grades) / len(all_grades), 2) if all_grades else 0
                # Передаём в шаблон
                return render_template('load_table.html',
                                       is_diploma = is_diploma,
                                       funck=funck,
                                       groups=groups,
                                       students=students,
                                       control_types=control_types,
                                       total_cols=total_cols,
                                       semester_filter=semester_filter,
                                       session=session)
            else:
                flash('У вас нет прав доступа к этому разделу.', 'danger')
                return redirect(url_for('index'))

        # Обработка других значений funck (если есть)
        case _:
            # Обработка неизвестного параметра функции
            flash('Неверный параметр функции', 'danger')
            return redirect(url_for('index'))


@app.route('/delete_recording/<id>', methods=['GET', 'POST'])
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
        # if not session.get('is_admin', False):
        flash('У вас нет прав на удаление пользователей.', 'danger')
        return redirect(url_for('load_table', funck='edit_users'))

        # if not session.get('is_specialist', False):
        flash('У вас нет прав на удаление дисциплины.', 'danger')
        return redirect(url_for('load_table', funck='edit_disciplines'))

        # Проверка, что пользователь не пытается удалить себя
        # if session['user_id'] == id:
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

            case 'edit_otdel':
                if not session.get('is_admin', False):  # Исправлено: is_admin вместо is_specialist
                    flash('У вас нет прав на удаление отдела.', 'danger')
                    return redirect(url_for('load_table', funck='edit_otdel'))

                conn.execute('DELETE FROM departments WHERE id_department = ?', (id,))
                conn.commit()
                flash('Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_otdel'))

            case 'edit_fgoss':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление учебного года.', 'danger')
                    return redirect(url_for('load_table', funck='edit_fgoss'))

                conn.execute('DELETE FROM fgoss WHERE id_fgos = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_fgoss'))

            case 'edit_nagruzka':
                if not session.get('is_specialist', False):
                    flash('У вас нет прав на удаление нагрузки.', 'danger')
                    return redirect(url_for('load_table', funck='edit_nagruzka'))

                conn = get_db_connection()
                try:
                    conn.execute('DELETE FROM workload WHERE id_load = ?', (id,))
                    conn.commit()
                    flash('Запись успешно удалена!', 'success')
                except Exception as e:
                    flash(f'Ошибка при удалении: {str(e)}', 'danger')
                finally:
                    conn.close()

                return redirect(url_for('load_table', funck='edit_nagruzka'))

            # СТУДЕНТЫ #

            case 'edit_students':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление студента.', 'danger')
                    return redirect(url_for('load_table', funck='edit_students'))

                conn.execute('DELETE FROM students WHERE id_student = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_students'))

            # ВИДЫ ВЕДОМОСТИ
            case 'edit_typesved':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление типа ведомости.', 'danger')
                    return redirect(url_for('load_table', funck='edit_typesved'))

                conn.execute('DELETE FROM statement_types WHERE id_type = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_typesved'))
            # ГРУППЫ
            case 'edit_groups':
                if not (session.get('is_zav', False)):
                    flash('У вас нет прав на удаление группы.', 'danger')
                    return redirect(url_for('load_table', funck='edit_groups'))

                conn.execute('DELETE FROM groups WHERE id_group = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_groups'))
            # ФОРМА ОБУЧЕНИЯ
            case 'edit_formobuch':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление формы обучения.', 'danger')
                    return redirect(url_for('load_table', funck='edit_formobuch'))

                conn.execute('DELETE FROM study_form WHERE id_form = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_formobuch'))
            # СПЕЦИАЛЬНОСТЬ
            case 'edit_spec':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление специальности.', 'danger')
                    return redirect(url_for('load_table', funck='edit_spec'))

                conn.execute('DELETE FROM specialties WHERE id_specialty = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_spec'))
            # ВЕДОМОСТЬ
            case 'edit_statement':
                if not session.get('is_zav', False):
                    flash('У вас нет прав на удаление ведомости.', 'danger')
                    return redirect(url_for('load_table', funck='edit_ved'))

                conn.execute('DELETE FROM statements WHERE id_statement = ?', (id,))
                conn.commit()
                flash(f'Запись успешно удалена!', 'success')
                return redirect(url_for('load_table', funck='edit_statement'))

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

    # return redirect(url_for('load_table', funck='edit_users'))


@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    funck = request.args.get('funck') or request.form.get('funck')

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

    if funck == 'edit_otdel':
        if session.get('is_admin', False):
            if request.method == 'GET':
                return render_template('add_info.html', funck=funck)

            # POST запрос - получаем funck из формы
            funck = request.form.get('funck')  # ВАЖНО: получаем funck из формы

            department_name = request.form.get('department_name', '').strip()
            errors = []

            if not department_name:
                errors.append('Название отделения обязательно')
            elif len(department_name) > 50:
                errors.append('Название отделения должно быть не более 50 символов')

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
                existing_department = conn.execute(
                    'SELECT id_department FROM departments WHERE department_name = ?',
                    (department_name,)
                ).fetchone()

                if existing_department:
                    flash('Такое отделение уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form
                    )

                # Вставка нового отделения
                conn.execute(
                    'INSERT INTO departments (department_name) VALUES (?)',
                    (department_name,)
                )
                conn.commit()
                flash(f'Отделение "{department_name}" успешно создано!', 'success')
                return redirect(url_for('load_table', funck='edit_otdel'))

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
            flash('У вас нет прав для добавления отделения', 'danger')
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

    # ДОБАВЛЕНИЕ НАГРУЗКИ
    if funck == 'edit_nagruzka':
        if session.get('is_specialist', False):
            # Вспомогательные функции для загрузки данных из БД
            def get_academic_years():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_year, year_name, winter_week, summer_week FROM academic_year ORDER BY year_name').fetchall()
                conn.close()
                return [{'id_year': row['id_year'], 'year_name': row['year_name'], 'winter_week': row['winter_week'],
                         'summer_week': row['summer_week']} for row in rows]

            def get_teachers():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name').fetchall()
                conn.close()
                return [{'id_user': row['id_user'], 'full_name': row['full_name']} for row in rows]

            def get_groups():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                conn.close()
                return [{'id_group': row['id_group']} for row in rows]

            def get_disciplines():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_discipline, discipline_name FROM disciplines ORDER BY discipline_name').fetchall()
                conn.close()
                return [{'id_discipline': row['id_discipline'], 'discipline_name': row['discipline_name']} for row in
                        rows]

            def get_fgos_list():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_fgos, name FROM fgoss ORDER BY name').fetchall()
                conn.close()
                return [{'id_fgos': row['id_fgos'], 'name': row['name']} for row in rows]

            # GET-запрос: показываем форму
            if request.method == 'GET':
                academic_years = get_academic_years()
                teachers = get_teachers()
                groups = get_groups()
                disciplines = get_disciplines()
                fgos_list = get_fgos_list()

                return render_template('add_info.html',
                                       funck=funck,
                                       academic_years=academic_years,
                                       teachers=teachers,
                                       groups=groups,
                                       disciplines=disciplines,
                                       fgos_list=fgos_list)

            # POST-запрос: обработка отправленной формы
            if request.method == 'POST':
                try:
                    # Получаем данные из формы
                    id_year = request.form.get('id_year')
                    id_teacher = request.form.get('id_teacher')
                    id_group = request.form.get('id_group')
                    id_discipline = request.form.get('id_discipline')
                    id_fgos = request.form.get('id_fgos')

                    # ❌ УБИРАЕМ weeks_winter и weeks_summer - они НЕ ДОЛЖНЫ БЫТЬ в таблице workload
                    # weeks_winter = int(request.form.get('weeks_winter', 0))
                    # weeks_summer = int(request.form.get('weeks_summer', 0))

                    # Зимний семестр
                    independent_winter = int(request.form.get('independent_winter', 0))
                    consultations_winter = int(request.form.get('consultations_winter', 0))
                    lectures_winter = int(request.form.get('lectures_winter', 0))
                    practice_winter = int(request.form.get('practice_winter', 0))
                    labs_winter = int(request.form.get('labs_winter', 0))
                    seminars_winter = int(request.form.get('seminars_winter', 0))
                    course_project_winter = int(request.form.get('course_project_winter', 0))
                    attestation_winter = int(request.form.get('attestation_winter', 0))

                    # Летний семестр
                    independent_summer = int(request.form.get('independent_summer', 0))
                    consultations_summer = int(request.form.get('consultations_summer', 0))
                    lectures_summer = int(request.form.get('lectures_summer', 0))
                    practice_summer = int(request.form.get('practice_summer', 0))
                    labs_summer = int(request.form.get('labs_summer', 0))
                    seminars_summer = int(request.form.get('seminars_summer', 0))
                    course_project_summer = int(request.form.get('course_project_summer', 0))
                    attestation_summer = int(request.form.get('attestation_summer', 0))

                    # ✅ ДОБАВЛЯЕМ экзамены, зачеты, дифф. зачеты
                    exam = int(request.form.get('exam', 0))
                    credit = int(request.form.get('credit', 0))
                    diff_credit = int(request.form.get('diff_credit', 0))

                    # Валидация
                    if not all([id_year, id_teacher, id_group, id_discipline, id_fgos]):
                        flash('Заполните все обязательные поля', 'danger')
                        return redirect(url_for('add_info', funck='edit_nagruzka'))

                    conn = get_db_connection()

                    # Проверка на дубликат
                    existing = conn.execute('''
                        SELECT id_load FROM workload 
                        WHERE id_year = ? AND id_teacher = ? AND id_group = ? AND id_discipline = ?
                    ''', (id_year, id_teacher, id_group, id_discipline)).fetchone()

                    if existing:
                        flash('Такая запись нагрузки уже существует для данной дисциплины, группы и преподавателя',
                              'danger')
                        conn.close()
                        return redirect(url_for('add_info', funck='edit_nagruzka'))

                    # ✅ ПРАВИЛЬНЫЙ INSERT - БЕЗ weeks_winter и weeks_summer, С exam, credit, diff_credit
                    conn.execute('''
                        INSERT INTO workload (
                            id_year, id_teacher, id_group, id_discipline, id_fgos,
                            independent_winter, consultations_winter, 
                            lectures_winter, practice_winter, labs_winter, seminars_winter, 
                            course_project_winter, attestation_winter,
                            independent_summer, consultations_summer,
                            lectures_summer, practice_summer, labs_summer, seminars_summer,
                            course_project_summer, attestation_summer,
                            exam, credit, diff_credit
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        id_year, id_teacher, id_group, id_discipline, id_fgos,
                        independent_winter, consultations_winter,
                        lectures_winter, practice_winter, labs_winter, seminars_winter,
                        course_project_winter, attestation_winter,
                        independent_summer, consultations_summer,
                        lectures_summer, practice_summer, labs_summer, seminars_summer,
                        course_project_summer, attestation_summer,
                        exam, credit, diff_credit
                    ))
                    conn.commit()
                    conn.close()

                    flash('Запись успешно добавлена!', 'success')
                    return redirect(url_for('load_table', funck='edit_nagruzka'))

                except Exception as e:
                    flash(f'Ошибка при добавлении нагрузки: {str(e)}', 'danger')
                    return redirect(url_for('add_info', funck='edit_nagruzka'))
        else:
            flash('У вас нет прав для добавления нагрузки', 'danger')
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

    # СТУДЕНТЫ
    if funck == 'edit_students':
        if session.get('is_zav', False):

            def get_groups():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                conn.close()
                return [{'id': row['id_group']} for row in rows]

            if request.method == 'GET':
                groups = get_groups()
                return render_template('add_info.html', funck=funck, group_list=groups)

            full_name = request.form.get('full_name', '')
            id_group = request.form.get('id_group')

            errors = []

            if not full_name:
                errors.append('ФИО обязательно')
            elif len(full_name) > 50:
                errors.append('ФИО должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z\s]+$', full_name):
                errors.append('ФИО может содержать буквы (русские/латинские) и пробелы')

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
                    group_list=groups
                )

            conn = get_db_connection()
            try:
                existing_student = conn.execute(
                    'SELECT id_student FROM students WHERE full_name = ? AND id_group = ?',
                    (full_name.strip(), id_group)
                ).fetchone()

                if existing_student:
                    flash('Студент с таким ФИО уже существует в этой группе', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        group_list=groups
                    )

                conn.execute('BEGIN TRANSACTION')
                conn.execute(
                    'INSERT INTO students (full_name, id_group) VALUES (?, ?)',
                    (full_name.strip(), id_group)
                )
                conn.commit()
                flash(f'Студент {full_name} успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_students'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template('add_info.html', funck=funck,
                                       form_data=request.form, groups=groups)

            finally:
                conn.close()

        else:
            flash('У вас нет прав для добавления студента', 'danger')
            return redirect(url_for('index'))

    # ВИДЫ ВЕДОМОСТИ
    if funck == 'edit_typesved':

        if session.get('is_zav', False):

            if request.method == 'GET':
                return render_template('add_info.html', funck=funck, session=session)

            type_name = request.form.get('typeved_name', '').strip()
            errors = []

            if not type_name:
                errors.append('Название типа ведомости обязательно')
            elif len(type_name) > 50:
                errors.append('Название типа ведомости должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.]+$', type_name):
                errors.append(
                    'Название типа ведомости может содержать буквы (русские/латинские), цифры, пробелы, дефисы и точки')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    session=session
                )

            conn = get_db_connection()
            try:
                existing_type = conn.execute(
                    'SELECT id_type FROM statement_types WHERE type_name = ?',
                    (type_name,)
                ).fetchone()

                if existing_type:
                    flash('Такой тип ведомости уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        session=session
                    )

                # Вставка новой записи
                conn.execute(
                    'INSERT INTO statement_types (type_name) VALUES (?)',
                    (type_name,)
                )
                conn.commit()
                flash(f'Тип ведомости "{type_name}" успешно создан!', 'success')
                return redirect(url_for('load_table', funck='edit_typesved'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    session=session
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления типа ведомости', 'danger')
            return redirect(url_for('index'))

    # ГРУППЫ
    if funck == 'edit_groups':
        if session.get('is_zav', False):
            def get_forms():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_form, form_name FROM study_form ORDER BY form_name').fetchall()
                conn.close()
                return [{'id': row['id_form'], 'name': row['form_name']} for row in rows]

            def get_prepod():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name').fetchall()
                conn.close()
                return [{'id': row['id_user'], 'name': row['full_name']} for row in rows]

            def get_specs():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_specialty, specialty_name FROM specialties ORDER BY specialty_name').fetchall()
                conn.close()
                return [{'id': row['id_specialty'], 'name': row['specialty_name']} for row in rows]

            if request.method == 'GET':
                forms = get_forms()
                prepods = get_prepod()
                specs = get_specs()
                return render_template('add_info.html',
                                       funck=funck,
                                       studyform_list=forms,
                                       classteach_list=prepods,
                                       spec_list=specs,
                                       session=session)

            group_name = request.form.get('group_name', '').strip()
            id_study_form = request.form.get('id_study_form', '')
            id_classteach = request.form.get('id_classteach', '')
            id_spec = request.form.get('id_spec', '')

            forms = get_forms()
            prepods = get_prepod()
            specs = get_specs()

            errors = []
            if not group_name:
                errors.append('Код группы обязательно')
            elif len(group_name) > 50:
                errors.append('Код группы должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.\/]+$', group_name):
                errors.append('Код группы может содержать только буквы, цифры, пробелы, дефисы, точки и слэш')
            if not id_study_form:
                errors.append('Выберите форму обучения')
            else:
                valid_form_ids = [str(f['id']) for f in forms]
                if id_study_form not in valid_form_ids:
                    errors.append('Выберите корректную форму обучения')
            if not id_classteach:
                errors.append('Выберите классного руководителя')
            else:
                valid_prepod_ids = [str(p['id']) for p in prepods]
                if id_classteach not in valid_prepod_ids:
                    errors.append('Выберите корректного классного руководителя')
            if not id_spec:
                errors.append('Выберите специальность')
            else:
                valid_spec_ids = [str(s['id']) for s in specs]
                if id_spec not in valid_spec_ids:
                    errors.append('Выберите корректную специальность')
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('add_info.html',
                                       funck=funck,
                                       form_data=request.form,
                                       studyform_list=forms,
                                       classteach_list=prepods,
                                       spec_list=specs,
                                       session=session)

            conn = get_db_connection()
            try:
                existing_group = conn.execute(
                    'SELECT id_group FROM groups WHERE id_group = ?',
                    (group_name,)
                ).fetchone()

                if existing_group:
                    flash('Такая группа уже существует', 'danger')
                    return render_template('add_info.html',
                                           funck=funck,
                                           form_data=request.form,
                                           studyform_list=forms,
                                           classteach_list=prepods,
                                           spec_list=specs,
                                           session=session)

                conn.execute('''
                    INSERT INTO groups 
                    (id_group, course_number, id_study_form, id_class_teacher, id_specialty)
                    VALUES (?, ?, ?, ?, ?)
                ''', (group_name, 1, int(id_study_form), int(id_classteach), id_spec))

                conn.commit()
                flash(f'Группа "{group_name}" успешно создана!', 'success')
                return redirect(url_for('load_table', funck='edit_groups'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template('add_info.html',
                                       funck=funck,
                                       form_data=request.form,
                                       studyform_list=forms,
                                       classteach_list=prepods,
                                       spec_list=specs,
                                       session=session)
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления группы', 'danger')
            return redirect(url_for('index'))

    # ФОРМА ОБУЧЕНИЯ
    if funck == 'edit_formobuch':

        if session.get('is_zav', False):

            if request.method == 'GET':
                return render_template('add_info.html', funck=funck, session=session)

            formobuch_name = request.form.get('formobuch_name', '').strip()  # Имя как в HTML
            errors = []

            if not formobuch_name:
                errors.append('Название формы обучения обязательно')
            elif len(formobuch_name) > 50:
                errors.append('Название формы обучения должно быть не более 50 символов')
            elif not re.match(r'^[а-яА-Яa-zA-Z\s\-]+$', formobuch_name):
                errors.append('Название формы обучения может содержать только буквы, пробелы и дефисы')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    session=session
                )

            conn = get_db_connection()
            try:
                existing_form = conn.execute(
                    'SELECT id_form FROM study_form WHERE form_name = ?',
                    (formobuch_name,)
                ).fetchone()

                if existing_form:
                    flash('Такая форма обучения уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        session=session
                    )

                conn.execute(
                    'INSERT INTO study_form (form_name) VALUES (?)',
                    (formobuch_name,)
                )
                conn.commit()
                flash(f'Форма обучения "{formobuch_name}" успешно создана!', 'success')
                return redirect(url_for('load_table', funck='edit_formobuch'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    session=session
                )
            finally:
                conn.close()
        else:
            flash('У вас нет прав для добавления форм обучения', 'danger')
            return redirect(url_for('index'))

    # СПЕЦИАЛЬНОСТИ
    if funck == 'edit_spec':
        if session.get('is_zav', False):

            def get_departs():
                conn = get_db_connection()
                rows = conn.execute(
                    'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                conn.close()
                return [{'id': row['id_department'], 'name': row['department_name']} for row in rows]

            if request.method == 'GET':
                departs = get_departs()
                return render_template('add_info.html', funck=funck, department_list=departs, session=session)

            id_specialty = request.form.get('id_specialty', '').strip()
            specialty_name = request.form.get('specialty_name', '').strip()
            id_department = request.form.get('id_department', '')

            errors = []

            if not id_specialty:
                errors.append('Код специальности обязателен')
            elif not re.match(r'^\d{2}\.\d{2}\.\d{2}$', id_specialty):
                errors.append('Неверный формат специальности. Пример: 38.02.01')

            if not specialty_name:
                errors.append('Название специальности обязательно')
            elif len(specialty_name) > 50:
                errors.append('Название специальности должно быть не более 50 символов')

            departs = get_departs()
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
                    department_list=departs,
                    session=session
                )

            conn = get_db_connection()
            try:
                existing_spec = conn.execute(
                    'SELECT id_specialty FROM specialties WHERE id_specialty = ?',
                    (id_specialty,)
                ).fetchone()

                if existing_spec:
                    flash('Специальность с таким кодом уже существует', 'danger')
                    return render_template(
                        'add_info.html',
                        funck=funck,
                        form_data=request.form,
                        department_list=departs,
                        session=session
                    )

                conn.execute('''
                    INSERT INTO specialties (id_specialty, specialty_name, id_department)
                    VALUES (?, ?, ?)
                ''', (id_specialty, specialty_name, int(id_department)))

                conn.commit()
                flash(f'Специальность "{specialty_name}" успешно создана!', 'success')
                return redirect(url_for('load_table', funck='edit_spec'))

            except sqlite3.Error as e:
                conn.rollback()
                flash(f'Ошибка базы данных: {str(e)}', 'danger')
                return render_template(
                    'add_info.html',
                    funck=funck,
                    form_data=request.form,
                    department_list=departs,
                    session=session
                )
            finally:
                conn.close()

    # ВЕДОМОСТИ
    if funck == 'edit_statement':
        if session.get('is_zav', False):

            def get_workload():
                conn = get_db_connection()
                rows = conn.execute('''
                            SELECT w.id_load, 
                                d.discipline_name || ', ' || g.id_group || ', ' || u.full_name AS description
                            FROM workload w
                            INNER JOIN disciplines d ON w.id_discipline = d.id_discipline
                            INNER JOIN groups g ON w.id_group = g.id_group
                            INNER JOIN users u ON w.id_teacher = u.id_user
                            ORDER BY description
                    ''').fetchall()
                conn.close()
                return [{'id': row['id_load'], 'name': row['description']} for row in rows]

            def get_typeved():
                conn = get_db_connection()
                rows = conn.execute('SELECT id_type, type_name FROM statement_types ORDER BY type_name').fetchall()
                conn.close()
                return [{'id': row['id_type'], 'name': row['type_name']} for row in rows]

            if request.method == 'GET':
                workload = get_workload()
                typeveds = get_typeved()
                return render_template('add_info.html',
                                       funck=funck,
                                       workload_list=workload,
                                       typeved_list=typeveds,
                                       session=session)

            id_load = request.form.get('id_load', '')
            id_typeved = request.form.get('id_typeved', '')
            semester = request.form.get('semester', '')
            is_diploma = request.form.get('is_diploma', '0')

            workload = get_workload()
            typesved = get_typeved()

            errors = []
            if not id_load:
                errors.append('Выберите нагрузку')
            else:
                valid_workload_ids = [str(w['id']) for w in workload]
                if id_load not in valid_workload_ids:
                    errors.append('Выберите корректную нагрузку')

            if not id_typeved:
                errors.append('Выберите тип ведомости')
            else:
                valid_typeved_ids = [str(t['id']) for t in typesved]
                if id_typeved not in valid_typeved_ids:
                    errors.append('Выберите корректный тип ведомости')

            if not semester:
                errors.append('Укажите семестр')
            else:
                try:
                    sem = int(semester)
                    if sem < 1 or sem > 8:
                        errors.append('Семестр должен быть от 1 до 8')
                except ValueError:
                    errors.append('Семестр должен быть числом')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template('add_info.html',
                                       funck=funck,
                                       workload_list=workload,
                                       typeved_list=typesved,
                                       session=session)

            conn = get_db_connection()
            try:
                existing_statement = conn.execute(
                    '''SELECT id_statement FROM statements 
                    WHERE id_discipline = ? AND id_type = ? AND semester = ?''',
                    (id_load, id_typeved, semester)
                ).fetchone()

                if existing_statement:
                    flash('Такая ведомость уже существует', 'danger')
                    return render_template('add_info.html',
                                           funck=funck,
                                           form_data=request.form,
                                           workload_list=workload,
                                           typeved_list=typesved,
                                           session=session)

                conn.execute('''
                        INSERT INTO statements 
                        (id_discipline, id_type, semester, is_diploma, created_at, status)
                        VALUES (?, ?, ?, ?, DATE('now'), 1)
                    ''', (id_load, id_typeved, semester, is_diploma))

                conn.commit()
                flash(f'Ведомость успешно создана!', 'success')
                return redirect(url_for('load_table', funck='edit_statement'))

            except sqlite3.Error as e:
                conn.rollback()
                print(f"!!! SQL ERROR: {e}")
                flash('Ошибка базы данных: {str(e)}', 'danger')
                return render_template('add_info.html',
                                       funck=funck,
                                       form_data=request.form,
                                       workload_list=workload,
                                       typeved_list=typesved,
                                       session=session)
            finally:
                conn.close()

        else:
            flash('У вас нет прав для добавления ведомости', 'danger')
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
                    rows = conn.execute(
                        'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
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

        case 'edit_otdel':
            if session.get('is_admin', False):
                department_id = request.args.get('department_id', type=int)
                if not department_id:
                    flash('Не указан ID отдела', 'danger')
                    return redirect(url_for('load_table', funck='edit_otdel'))

                conn = get_db_connection()

                if request.method == 'GET':
                    department = conn.execute('''
                               SELECT id_department, department_name
                               FROM departments
                               WHERE id_department = ?
                           ''', (department_id,)).fetchone()
                    conn.close()

                    if not department:
                        flash('Отдел не найден.', 'danger')
                        return redirect(url_for('load_table', funck='edit_otdel'))

                    return render_template('edit_info.html',
                                           funck=funck,
                                           department=department)

                # POST — сохраняем изменения
                if request.method == 'POST':
                    department_name = request.form.get('department_name', '').strip()

                    errors = []
                    if not department_name:
                        errors.append('Название отдела обязательно')
                    elif len(department_name) > 50:
                        errors.append('Название отдела не может быть длиннее 50 символов')

                    if errors:
                        for error in errors:
                            flash(error, 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               department={'id_department': department_id,
                                                           'department_name': department_name})

                    try:
                        conn.execute('''
                                   UPDATE departments
                                   SET department_name = ?
                                   WHERE id_department = ?
                               ''', (department_name, department_id))
                        conn.commit()
                        flash('Данные отдела успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_otdel'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               department={'id_department': department_id,
                                                           'department_name': department_name})
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

        case 'edit_nagruzka':
            if session.get('is_specialist', False):

                def get_academic_years():
                    conn = get_db_connection()
                    rows = conn.execute(
                        'SELECT id_year, year_name, winter_week, summer_week FROM academic_year ORDER BY year_name').fetchall()
                    conn.close()
                    return [
                        {'id_year': row['id_year'], 'year_name': row['year_name'], 'winter_week': row['winter_week'],
                         'summer_week': row['summer_week']} for row in rows]

                def get_teachers():
                    conn = get_db_connection()
                    rows = conn.execute(
                        'SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name').fetchall()
                    conn.close()
                    return [{'id_user': row['id_user'], 'full_name': row['full_name']} for row in rows]

                def get_groups():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                    conn.close()
                    return [{'id_group': row['id_group']} for row in rows]

                def get_disciplines():
                    conn = get_db_connection()
                    rows = conn.execute(
                        'SELECT id_discipline, discipline_name FROM disciplines ORDER BY discipline_name').fetchall()
                    conn.close()
                    return [{'id_discipline': row['id_discipline'], 'discipline_name': row['discipline_name']} for row
                            in rows]

                def get_fgos_list():
                    conn = get_db_connection()
                    rows = conn.execute('SELECT id_fgos, name FROM fgoss ORDER BY name').fetchall()
                    conn.close()
                    return [{'id_fgos': row['id_fgos'], 'name': row['name']} for row in rows]

                # Получаем ID нагрузки из аргументов
                id_load = request.args.get('id_load', type=int)
                if not id_load:
                    flash('Не указан ID нагрузки', 'danger')
                    return redirect(url_for('load_table', funck='edit_nagruzka'))

                conn = get_db_connection()
                load = conn.execute('SELECT * FROM workload WHERE id_load = ?', (id_load,)).fetchone()
                conn.close()

                if not load:
                    flash('Нагрузка не найдена.', 'danger')
                    return redirect(url_for('load_table', funck='edit_nagruzka'))

                # Загружаем списки для выпадающих списков
                academic_years = get_academic_years()
                teachers = get_teachers()
                groups = get_groups()
                disciplines = get_disciplines()
                fgos_list = get_fgos_list()

                # GET – показываем форму
                if request.method == 'GET':
                    return render_template('edit_info.html',
                                           funck=funck,
                                           load=load,
                                           academic_years=academic_years,
                                           teachers=teachers,
                                           groups=groups,
                                           disciplines=disciplines,
                                           fgos_list=fgos_list,
                                           is_specialist=session.get('is_specialist', False))

                # POST – обрабатываем сохранение
                id_year = request.form.get('id_year', type=int)
                id_teacher = request.form.get('id_teacher', type=int)
                id_group = request.form.get('id_group')
                id_discipline = request.form.get('id_discipline')
                id_fgos = request.form.get('id_fgos', type=int)

                # Получаем числовые значения с проверкой
                def get_int_value(key, default=0):
                    try:
                        return int(request.form.get(key, default))
                    except (ValueError, TypeError):
                        return default

                independent_winter = get_int_value('independent_winter')
                consultations_winter = get_int_value('consultations_winter')
                lectures_winter = get_int_value('lectures_winter')
                practice_winter = get_int_value('practice_winter')
                labs_winter = get_int_value('labs_winter')
                seminars_winter = get_int_value('seminars_winter')
                course_project_winter = get_int_value('course_project_winter')
                attestation_winter = get_int_value('attestation_winter')

                independent_summer = get_int_value('independent_summer')
                consultations_summer = get_int_value('consultations_summer')
                lectures_summer = get_int_value('lectures_summer')
                practice_summer = get_int_value('practice_summer')
                labs_summer = get_int_value('labs_summer')
                seminars_summer = get_int_value('seminars_summer')
                course_project_summer = get_int_value('course_project_summer')
                attestation_summer = get_int_value('attestation_summer')

                exam = get_int_value('exam')
                credit = get_int_value('credit')
                diff_credit = get_int_value('diff_credit')

                # Валидация
                errors = []

                if not id_year:
                    errors.append('Выберите год обучения')
                if not id_teacher:
                    errors.append('Выберите преподавателя')
                if not id_group:
                    errors.append('Выберите группу')
                if not id_discipline:
                    errors.append('Выберите дисциплину')
                if not id_fgos:
                    errors.append('Выберите ФГОС')

                if errors:
                    for error in errors:
                        flash(error, 'danger')
                    return render_template('edit_info.html',
                                           funck=funck,
                                           load=load,
                                           academic_years=academic_years,
                                           teachers=teachers,
                                           groups=groups,
                                           disciplines=disciplines,
                                           fgos_list=fgos_list,
                                           is_specialist=session.get('is_specialist', False),
                                           form_data=request.form)

                conn = get_db_connection()
                try:
                    # Проверка на дубликат (исключая текущую запись)
                    existing = conn.execute('''
                        SELECT id_load FROM workload 
                        WHERE id_year = ? AND id_teacher = ? AND id_group = ? AND id_discipline = ?
                        AND id_load != ?
                    ''', (id_year, id_teacher, id_group, id_discipline, id_load)).fetchone()

                    if existing:
                        flash('Такая запись нагрузки уже существует для данной дисциплины, группы и преподавателя',
                              'danger')
                        conn.close()
                        return render_template('edit_info.html',
                                               funck=funck,
                                               load=load,
                                               academic_years=academic_years,
                                               teachers=teachers,
                                               groups=groups,
                                               disciplines=disciplines,
                                               fgos_list=fgos_list,
                                               is_specialist=session.get('is_specialist', False),
                                               form_data=request.form)

                    # Обновление записи
                    conn.execute('''
                        UPDATE workload SET
                            id_year = ?,
                            id_teacher = ?,
                            id_group = ?,
                            id_discipline = ?,
                            id_fgos = ?,
                            exam = ?,
                            credit = ?,
                            diff_credit = ?,
                            independent_winter = ?,
                            consultations_winter = ?,
                            lectures_winter = ?,
                            practice_winter = ?,
                            labs_winter = ?,
                            seminars_winter = ?,
                            course_project_winter = ?,
                            attestation_winter = ?,
                            independent_summer = ?,
                            consultations_summer = ?,
                            lectures_summer = ?,
                            practice_summer = ?,
                            labs_summer = ?,
                            seminars_summer = ?,
                            course_project_summer = ?,
                            attestation_summer = ?
                        WHERE id_load = ?
                    ''', (
                        id_year, id_teacher, id_group, id_discipline, id_fgos,
                        exam, credit, diff_credit,
                        independent_winter, consultations_winter, lectures_winter,
                        practice_winter, labs_winter, seminars_winter,
                        course_project_winter, attestation_winter,
                        independent_summer, consultations_summer, lectures_summer,
                        practice_summer, labs_summer, seminars_summer,
                        course_project_summer, attestation_summer,
                        id_load
                    ))

                    conn.commit()
                    flash('Изменения успешно сохранены!', 'success')
                    conn.close()
                    return redirect(url_for('load_table', funck='edit_nagruzka'))

                except sqlite3.Error as e:
                    conn.rollback()
                    flash(f'Ошибка базы данных: {str(e)}', 'danger')
                    conn.close()
                    return render_template('edit_info.html',
                                           funck=funck,
                                           load=load,
                                           academic_years=academic_years,
                                           teachers=teachers,
                                           groups=groups,
                                           disciplines=disciplines,
                                           fgos_list=fgos_list,
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

        # СТУДЕНТЫ #

        case 'edit_students':
            if session.get('is_zav', False):
                # Получаем ID студента
                id_student = request.args.get('id_student', type=int)
                if not id_student:
                    flash('Не указан ID студента', 'danger')
                    return redirect(url_for('load_table', funck='edit_students'))

                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':
                    student = conn.execute('''
                        SELECT id_student, full_name, id_group
                        FROM students
                        WHERE id_student = ?
                    ''', (id_student,)).fetchone()

                    # Получаем список групп для выпадающего списка
                    groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                    conn.close()

                    if not student:
                        flash('Студент не найден.', 'danger')
                        return redirect(url_for('load_table', funck='edit_students'))

                    return render_template('edit_info.html',
                                           funck=funck,
                                           student=student,
                                           groups=groups,
                                           session=session)

                # POST — сохраняем изменения
                if request.method == 'POST':
                    full_name = request.form.get('full_name', '').strip()
                    id_group = request.form.get('id_group', '')

                    errors = []
                    if not full_name:
                        errors.append('ФИО обязательно')
                    elif len(full_name) > 50:
                        errors.append('ФИО не может быть длиннее 50 символов')
                    elif not re.match(r'^[а-яА-Яa-zA-Z\s\-\.]+$', full_name):
                        errors.append('ФИО может содержать только буквы, пробелы, дефисы и точки')

                    if not id_group:
                        errors.append('Выберите группу')

                    if errors:
                        # Получаем данные студента и групп для повторного отображения
                        student = conn.execute('''
                            SELECT id_student, full_name, id_group
                            FROM students
                            WHERE id_student = ?
                        ''', (id_student,)).fetchone()
                        groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                        conn.close()

                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               student=student,
                                               groups=groups,
                                               form_data=request.form,
                                               session=session)

                    # Обновление в базе
                    try:
                        conn.execute('''
                            UPDATE students
                            SET full_name = ?, id_group = ?
                            WHERE id_student = ?
                        ''', (full_name, id_group, id_student))
                        conn.commit()
                        flash('Данные студента успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_students'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()

                        student = conn.execute('''
                            SELECT id_student, full_name, id_group
                            FROM students
                            WHERE id_student = ?
                        ''', (id_student,)).fetchone()
                        groups = conn.execute('SELECT id_group FROM groups ORDER BY id_group').fetchall()
                        conn.close()

                        return render_template('edit_info.html',
                                               funck=funck,
                                               student=student,
                                               groups=groups,
                                               session=session)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # ВИДЫ ВЕДОМОСТИ #

        case 'edit_typesved':
            if session.get('is_zav', False):
                # Получаем ID вида ведомости
                id_type = request.args.get('id_type', type=int)
                if not id_type:
                    flash('Не указан ID вида ведомости', 'danger')
                    return redirect(url_for('load_table', funck='edit_typesved'))

                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':
                    typeved = conn.execute('''
                        SELECT id_type, type_name
                        FROM statement_types
                        WHERE id_type = ?
                    ''', (id_type,)).fetchone()

                    if not typeved:
                        flash('Вид ведомости не найден.', 'danger')
                        return redirect(url_for('load_table', funck='edit_typesved'))

                    return render_template('edit_info.html',
                                           funck=funck,
                                           typeved=typeved,
                                           session=session)

                # POST — сохраняем изменения
                if request.method == 'POST':
                    type_name = request.form.get('type_name', '').strip()

                    errors = []
                    if not type_name:
                        errors.append('Название вида ведомости обязательно')
                    elif len(type_name) > 50:
                        errors.append('Вид ведомости не может быть длиннее 50 символов')
                    elif not re.match(r'^[а-яА-Яa-zA-Z\s\-\.]+$', type_name):
                        errors.append('Вид ведомости может содержать только буквы, пробелы, дефисы и точки')

                    if errors:
                        # Получаем данные для повторного отображения
                        typeved = conn.execute('''
                            SELECT id_type, type_name
                            FROM statement_types
                            WHERE id_type = ?
                        ''', (id_type,)).fetchone()
                        conn.close()

                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               typeved=typeved,
                                               form_data=request.form,
                                               session=session)

                    # Обновление в базе
                    try:
                        conn.execute('''
                            UPDATE statement_types
                            SET type_name = ?
                            WHERE id_type = ?
                        ''', (type_name, id_type))
                        conn.commit()
                        flash('Данные вида ведомости успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_typesved'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()

                        typeved = conn.execute('''
                            SELECT id_type, type_name
                            FROM statement_types
                            WHERE id_type = ?
                        ''', (id_type,)).fetchone()
                        conn.close()

                        return render_template('edit_info.html',
                                               funck=funck,
                                               typeved=typeved,
                                               session=session)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # ГРУППЫ

        case 'edit_groups':
            if session.get('is_zav', False):
                # Получаем ID группы
                id_group = request.args.get('id_group', '')

                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':
                    group = conn.execute('''
                        SELECT id_group, course_number, id_study_form, id_class_teacher, id_specialty
                        FROM groups
                        WHERE id_group = ?
                    ''', (id_group,)).fetchone()

                    if not group:
                        conn.close()
                        flash('Группа не найдена.', 'danger')
                        return redirect(url_for('load_table', funck='edit_groups'))

                    # Получаем списки для выпадающих списков
                    studyform_list = conn.execute(
                        'SELECT id_form, form_name FROM study_form ORDER BY form_name'
                    ).fetchall()

                    classteach_list = conn.execute(
                        'SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name'
                    ).fetchall()

                    spec_list = conn.execute(
                        'SELECT id_specialty, specialty_name FROM specialties ORDER BY specialty_name'
                    ).fetchall()

                    conn.close()

                    return render_template('edit_info.html',
                                           funck=funck,
                                           group=group,
                                           studyform_list=studyform_list,
                                           classteach_list=classteach_list,
                                           spec_list=spec_list,
                                           session=session)

                # POST — сохраняем изменения
                if request.method == 'POST':
                    id_group_old = request.form.get('id_group_old', '')
                    id_group_new = request.form.get('id_group', '').strip()
                    course_number = request.form.get('course_number', '')
                    id_study_form = request.form.get('id_study_form', '')
                    id_classteach = request.form.get('id_classteach', '')
                    id_spec = request.form.get('id_spec', '')

                    # Получаем списки для повторного отображения при ошибках
                    studyform_list = conn.execute(
                        'SELECT id_form, form_name FROM study_form ORDER BY form_name'
                    ).fetchall()

                    classteach_list = conn.execute(
                        'SELECT id_user, full_name FROM users WHERE id_role = 4 ORDER BY full_name'
                    ).fetchall()

                    spec_list = conn.execute(
                        'SELECT id_specialty, specialty_name FROM specialties ORDER BY specialty_name'
                    ).fetchall()

                    # Валидация
                    errors = []

                    if not id_group_new:
                        errors.append('Код группы обязателен')
                    elif len(id_group_new) > 50:
                        errors.append('Код группы не может быть длиннее 50 символов')
                    elif not re.match(r'^[а-яА-Яa-zA-Z0-9\s\-\.\/]+$', id_group_new):
                        errors.append('Код группы содержит недопустимые символы')

                    if not course_number:
                        errors.append('Номер курса обязателен')
                    elif not course_number.isdigit():
                        errors.append('Номер курса должен быть числом')

                    if not id_study_form:
                        errors.append('Выберите форму обучения')

                    if not id_classteach:
                        errors.append('Выберите классного руководителя')

                    if not id_spec:
                        errors.append('Выберите специальность')

                    if errors:
                        conn.close()
                        # Создаём объект group для повторного отображения формы
                        group = {
                            'id_group': id_group_new,
                            'course_number': course_number,
                            'id_study_form': int(id_study_form) if id_study_form else None,
                            'id_class_teacher': int(id_classteach) if id_classteach else None,
                            'id_specialty': id_spec
                        }
                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               group=group,
                                               studyform_list=studyform_list,
                                               classteach_list=classteach_list,
                                               spec_list=spec_list,
                                               form_data=request.form,
                                               session=session)

                    # Обновление в базе
                    try:
                        conn.execute('''
                            UPDATE groups
                            SET id_group = ?, 
                                course_number = ?, 
                                id_study_form = ?, 
                                id_class_teacher = ?, 
                                id_specialty = ?
                            WHERE id_group = ?
                        ''', (
                            id_group_new,
                            int(course_number),
                            int(id_study_form),
                            int(id_classteach),
                            id_spec,
                            id_group_old
                        ))
                        conn.commit()
                        flash('Данные группы успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_groups'))

                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')
                        conn.close()

                        # Создаём объект group для повторного отображения
                        group = {
                            'id_group': id_group_new,
                            'course_number': course_number,
                            'id_study_form': int(id_study_form) if id_study_form else None,
                            'id_class_teacher': int(id_classteach) if id_classteach else None,
                            'id_specialty': id_spec
                        }

                        return render_template('edit_info.html',
                                               funck=funck,
                                               group=group,
                                               studyform_list=studyform_list,
                                               classteach_list=classteach_list,
                                               spec_list=spec_list,
                                               form_data=request.form,
                                               session=session)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # ФОРМА ОБУЧЕНИЯ

        case 'edit_formobuch':
            if session.get('is_zav', False):
                # Получаем ID
                id_form = request.args.get('id_form', type=int)
                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':

                    formobuch = conn.execute('''
                        SELECT id_form, form_name
                        FROM study_form
                        WHERE id_form = ?
                    ''', (id_form,)).fetchone()

                    if not formobuch:
                        flash('Форма обучения не найдена.', 'danger')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_formobuch'))

                    conn.close()
                    return render_template('edit_info.html',
                                           funck=funck,
                                           formobuch=formobuch,
                                           session=session)

                # POST — сохраняем изменения
                if request.method == 'POST':

                    form_name = request.form.get('form_name', '').strip()
                    # Пробуем получить ID из формы
                    id_form = request.form.get('id_form', type=int)

                    # Если нет в форме, пробуем из URL
                    if not id_form:
                        id_form = request.args.get('id_form', type=int)
                        print(f"ID из URL: {id_form}")

                    if not id_form:
                        print("ID не найден ни в форме, ни в URL")
                        flash('Не указан ID формы обучения', 'danger')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_formobuch'))

                    print(f"Итоговый ID: {id_form}")

                    errors = []
                    if not form_name:
                        errors.append('Название формы обучения обязательно')
                    elif len(form_name) > 50:
                        errors.append('Форма обучения не может быть длиннее 50 символов')
                    elif not re.match(r'^[а-яА-Яa-zA-Z\s\-\.]+$', form_name):
                        errors.append('Форма обучения может содержать только буквы, пробелы, дефисы и точки')

                    if errors:
                        # Получаем данные для повторного отображения
                        formobuch = conn.execute('''
                            SELECT id_form, form_name
                            FROM study_form
                            WHERE id_form = ?
                        ''', (id_form,)).fetchone()
                        conn.close()

                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               formobuch=formobuch,
                                               session=session)

                    # Обновление в базе
                    try:
                        conn.execute('''
                            UPDATE study_form
                            SET form_name = ?
                            WHERE id_form = ?
                        ''', (form_name, id_form))
                        conn.commit()
                        flash('Данные формы обучения успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_formobuch'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')

                        formobuch = conn.execute('''
                            SELECT id_form, form_name
                            FROM study_form
                            WHERE id_form = ?
                        ''', (id_form,)).fetchone()
                        conn.close()

                        return render_template('edit_info.html',
                                               funck=funck,
                                               formobuch=formobuch,
                                               session=session)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # СПЕЦИАЛЬНОСТЬ

        case 'edit_spec':
            if session.get('is_zav', False):
                # Получаем ID из разных источников
                id_specialty = request.args.get('id_specialty')
                if not id_specialty:
                    flash('Не указан ID специальности', 'danger')
                    return redirect(url_for('load_table', funck='edit_spec'))

                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':
                    specialty = conn.execute('''
                        SELECT id_specialty, specialty_name, id_department
                        FROM specialties
                        WHERE id_specialty = ?
                    ''', (id_specialty,)).fetchone()
                    departments = conn.execute(
                        'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                    conn.close()

                    if not specialty:
                        flash('Специальность не найдена.', 'danger')
                        return redirect(url_for('load_table', funck='edit_spec'))

                    return render_template('edit_info.html',
                                           funck=funck,
                                           spec=specialty,
                                           departments=departments,
                                           session=session)

                # POST — сохраняем изменения
                if request.method == 'POST':
                    id_specialty_new = request.form.get('id_specialty', '').strip()
                    specialty_name = request.form.get('specialty_name', '').strip()
                    id_department = request.form.get('id_department', '')

                    # Получаем оригинальный id_specialty из URL для WHERE
                    id_specialty_old = id_specialty

                    errors = []
                    if not id_specialty_new:
                        errors.append('Код специальности обязателен')
                    elif len(id_specialty_new) > 50:
                        errors.append('Код специальности не может быть длиннее 50 символов')
                    elif not re.match(r'^[\d\.]+$', id_specialty_new):
                        errors.append('Код специальности может содержать только цифры и точки')

                    if not specialty_name:
                        errors.append('Название специальности обязательно')
                    elif len(specialty_name) > 100:
                        errors.append('Название специальности не может быть длиннее 100 символов')
                    elif not re.match(r'^[а-яА-Яa-zA-Z\s\-\.]+$', specialty_name):
                        errors.append('Название специальности может содержать только буквы, пробелы, дефисы и точки')

                    if not id_department:
                        errors.append('Выберите отделение')

                    if errors:
                        # Получаем данные для повторного отображения
                        specialty = {
                            'id_specialty': id_specialty_new,
                            'specialty_name': specialty_name,
                            'id_department': int(id_department) if id_department else None
                        }
                        departments = conn.execute(
                            'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                        conn.close()

                        for error in errors:
                            flash(error, 'danger')
                        return render_template('edit_info.html',
                                               funck=funck,
                                               spec=specialty,
                                               departments=departments,
                                               session=session)

                    # Обновление в базе
                    try:
                        conn.execute('''
                            UPDATE specialties
                            SET id_specialty = ?, specialty_name = ?, id_department = ?
                            WHERE id_specialty = ?
                        ''', (id_specialty_new, specialty_name, int(id_department), id_specialty_old))
                        conn.commit()
                        flash('Данные специальности успешно обновлены', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_spec'))
                    except sqlite3.Error as e:
                        conn.rollback()
                        flash(f'Ошибка базы данных: {str(e)}', 'danger')

                        specialty = {
                            'id_specialty': id_specialty_new,
                            'specialty_name': specialty_name,
                            'id_department': int(id_department) if id_department else None
                        }
                        departments = conn.execute(
                            'SELECT id_department, department_name FROM departments ORDER BY department_name').fetchall()
                        conn.close()

                        return render_template('edit_info.html',
                                               funck=funck,
                                               spec=specialty,
                                               departments=departments,
                                               session=session)

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # ВЕДОМОСТЬ

        case 'edit_statement':
            if session.get('is_zav', False) or session.get('is_prepod', False):
                # Получаем ID из разных источников
                id_statement = request.args.get('id_statement')
                if not id_statement:
                    flash('Не указан ID ведомости', 'danger')
                    return redirect(url_for('load_table', funck='edit_statement'))
                if request.args.get('export') == 'pdf':
                    return export_statement_pdf(id_statement)
                conn = get_db_connection()

                # GET — показываем форму
                if request.method == 'GET':
                    statement = conn.execute('''
                        SELECT 
                            statements.id_statement,
                            specialties.specialty_name,
                            academic_year.year_name,
                            groups.course_number,
                            workload.id_group,
                            statements.semester,
                            disciplines.discipline_name,
                            users.full_name,
                            statements.status,
                            statements.filled_at,
                            statements.excused,
                            statements.unexcused   
                        FROM statements
                        LEFT JOIN workload ON statements.id_discipline = workload.id_load
                        LEFT JOIN academic_year ON workload.id_year = academic_year.id_year
                        LEFT JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
                        LEFT JOIN groups ON workload.id_group = groups.id_group 
                        LEFT JOIN users ON workload.id_teacher = users.id_user
                        LEFT JOIN specialties ON groups.id_specialty = specialties.id_specialty
                        WHERE statements.id_statement = ?
                    ''', (id_statement,)).fetchone()

                    student = conn.execute('''
                            SELECT 
                                students.full_name,
                                students.id_student,
                                grades.grade
                            FROM students
                            LEFT JOIN grades ON students.id_student = grades.id_student 
                                AND grades.id_statement = ?
                            WHERE students.id_group = ?''', (id_statement, statement['id_group'])).fetchall()

                    # Иницилизация счетчиков
                    grade_A = 0
                    grade_B = 0
                    grade_C = 0
                    grade_D = 0
                    grades_all = 0
                    not_been = 0

                    for stud in student:
                        if stud['grade'] == 5:
                            grade_A += 1
                        elif stud['grade'] == 4:
                            grade_B += 1
                        elif stud['grade'] == 3:
                            grade_C += 1
                        elif stud['grade'] == 2:
                            grade_D += 1
                        elif stud['grade'] == 0:
                            not_been += 1
                    grades_all = grade_A + grade_B + grade_C + grade_D

                    conn.close()

                    if not statement:
                        flash('Ведомость не найдена.', 'danger')
                        return redirect(url_for('load_table', funck='edit_statement'))
                    

                    return render_template('edit_info.html',
                                           funck=funck,
                                           statement=statement,
                                           students=student,
                                           grade_A=grade_A,
                                           grade_B=grade_B,
                                           grade_C=grade_C,
                                           grade_D=grade_D,
                                           grades_all=grades_all,
                                           not_been=not_been,
                                           session=session)

                conn = get_db_connection()
                
                # POST — сохраняем изменения
                if request.method == 'POST':
                    if request.args.get('action') == 'submit':
                        filled_at = request.form.get('filled_at', '')
                        conn.execute('UPDATE statements SET status = 1, filled_at = ? WHERE id_statement = ?', (filled_at, id_statement,))
                        conn.commit()
                        flash('Ведомость сдана!', 'success')
                        conn.close()
                        return redirect(url_for('load_table', funck='edit_statement', id_statement=id_statement))

                    excused = request.form.get('excused', '')
                    unexcused = request.form.get('unexcused', '')
                    id_grade = request.form.get('id_grade', '')
                    errors = []

                    if not excused:
                        errors.append('Количество н/я по уважительной причине обязательно')
                    elif not re.match(r'^[\d]+$', excused):
                        errors.append('Количество н/я по уважительной причине может содержать только цифры и числа')

                    if not unexcused:
                        errors.append('Количество н/я по неуважительной причине обязательно')
                    elif not re.match(r'^[\d]+$', unexcused):
                        errors.append('Количество н/я по неуважительной причине может содержать только цифры и числа')
                    
                    print("DEBUG: errors =", errors)
                    if errors:
                        statement = conn.execute('''
                            SELECT 
                                statements.id_statement,
                                specialties.specialty_name,
                                academic_year.year_name,
                                groups.course_number,
                                workload.id_group,
                                statements.semester,
                                disciplines.discipline_name,
                                users.full_name,
                                statements.status,
                                statements.filled_at,
                                statements.excused,
                                statements.unexcused   
                            FROM statements
                            LEFT JOIN workload ON statements.id_discipline = workload.id_load
                            LEFT JOIN academic_year ON workload.id_year = academic_year.id_year
                            LEFT JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
                            LEFT JOIN groups ON workload.id_group = groups.id_group 
                            LEFT JOIN users ON workload.id_teacher = users.id_user
                            LEFT JOIN specialties ON groups.id_specialty = specialties.id_specialty
                            WHERE statements.id_statement = ?
                        ''', (id_statement,)).fetchone()

                        student = conn.execute('''
                            SELECT 
                                students.full_name,
                                students.id_student,
                                grades.grade
                            FROM students
                            LEFT JOIN grades ON students.id_student = grades.id_student 
                                AND grades.id_statement = ?
                            WHERE students.id_group = ?''', (id_statement, statement['id_group'])).fetchall()
                        for error in errors:
                                flash(error, 'danger')
                        return render_template('edit_info.html', 
                                        funck=funck, 
                                        statement=statement, 
                                        students=student,
                                        session=session)
                    else:
                        filled_at = request.form.get('filled_at', '')
                        statement = conn.execute('''
                            SELECT 
                                statements.id_statement,
                                specialties.specialty_name,
                                academic_year.year_name,
                                groups.course_number,
                                workload.id_group,
                                statements.semester,
                                disciplines.discipline_name,
                                users.full_name,
                                statements.status,
                                statements.filled_at,
                                statements.excused,
                                statements.unexcused   
                                FROM statements
                                INNER JOIN workload ON statements.id_discipline = workload.id_load
                                INNER JOIN academic_year ON workload.id_year = academic_year.id_year
                                INNER JOIN disciplines ON workload.id_discipline = disciplines.id_discipline
                                INNER JOIN groups ON workload.id_group = groups.id_group 
                                INNER JOIN users ON workload.id_teacher = users.id_user
                                INNER JOIN specialties ON groups.id_specialty = specialties.id_specialty
                                WHERE statements.id_statement = ?
                        ''', (id_statement,)).fetchone()
                        student = conn.execute('''
                            SELECT students.id_student FROM students WHERE students.id_group = ?''',
                                            (statement['id_group'],)).fetchall()

                    for stud in student:
                        id_stud = stud['id_student']
                        key = f"grade_{id_stud}"
                        grade_value = request.form.get(key, '')
                        if grade_value != "":
                            conn.execute('''
                                INSERT OR REPLACE INTO grades (id_student, id_statement, grade) VALUES (?, ?, ?)
                                ''', (id_stud, id_statement, grade_value,))

                    conn.execute(''' UPDATE statements SET excused = ?,  unexcused = ?, filled_at = ? WHERE id_statement = ?''',
                                 (excused, unexcused, filled_at, id_statement,))
                    conn.commit()
                    conn.close()
                    flash('Ведомость успешно сохранена!', 'success')
                return redirect(url_for('load_table', funck='edit_statement'))

            else:
                flash('У вас нет прав доступа.', 'danger')
                return redirect(url_for('index'))

        # Обработка других значений funck (если есть)
        case _:
            # Обработка неизвестного параметра функции
            flash('Неверный параметр функции', 'danger')
            return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("❌ Ошибка базы данных: База данных не найдена")
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)