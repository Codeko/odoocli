#!/usr/bin/env python3

import argparse
import calendar
import codecs
import csv
import getpass
import io
import os
import smtplib
import sys
import time
import xmlrpc.client
from configparser import ConfigParser
from datetime import datetime, date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from string import Template

from dotenv import load_dotenv

labor_hours_by_day = 7.0


def memoize(func):
    func_name = func.__name__
    data = {}

    def wrappeada(login, month=None, year=None):

        if year is None:
            year = int(datetime.now().year)
        if month is None:
            month = int(datetime.now().month)

        if 'user_email' in login:
            user = login['user_email']
        else:
            user = login['username']

        dict_key = "{}-{}-{}-{}".format(func_name, user, month, year)

        if dict_key in data:
            return data[dict_key]
        else:
            data[dict_key] = list(func(login, month, year))
            return data[dict_key]

    return wrappeada


def show_resume_now(login, month=None, year=None):
    """
    Informe del mes corriente:
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    w_hours = count_worked_hours(login)
    l_hours = labor_hours_until_today(login)

    print("Resumen {} {}:".format(mes(month), year))
    print("Días laborables de este mes:\t{}".format(
        count_labour_days(login)))
    print("Horas laborables de este mes:\t{:.2f}".format(
        total_labor_hours(login)))
    print('Horas laborables hasta hoy:\t{:.2f}'.format(
        l_hours))
    print('Horas trabajadas hasta ahora:\t{:.2f}'.format(
        w_hours))
    print('Horas de diferencia:\t{:.2f}'.format(
        w_hours - l_hours))


def show_resume(login, month=None, year=None):
    """
    Informe del mes pasado como argumento:
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    print("{} {}\n".format(mes(month), year))
    print(resume_to_string(login, month, year))


def resume_to_string(login, month=None, year=None):
    """
    Informe del mes pasado como argumento:
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    w_hours = count_worked_hours(login, month, year)
    l_hours = total_labor_hours(login, month, year)

    response = "Resumen {} {}:\n".format(mes(month), year)
    response += "Días laborables:\t{}\n".format(
        count_labour_days(login, month, year))
    response += "Horas laborables:\t{:.2f}\n".format(l_hours)
    response += "Horas trabajadas:\t{:.2f}\n".format(w_hours)
    response += "Horas de diferencia:\t{:.2f}\n".format(w_hours - l_hours)
    return response


def year_summary(login, month=None, year=None):
    """
    resumen desde enero hasta el mes indicado
    """

    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    prev_mont = month - 1
    prev_year = year
    if prev_mont == 0:
        prev_mont = 12
        prev_year -= 1

    show_resume_now(login, month, year)
    print('\n')
    print(accumulated_summary(login, prev_mont, prev_year))


def accumulated_summary(login, month=None, year=None):
    """
    resumen desde enero hasta el mes indicado
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    labor_hours = 0
    worked_hours = 0

    for m in range(1, month + 1):
        labor_hours += total_labor_hours(login, m, year)
        worked_hours += count_worked_hours(login, m, year)
    response = 'Acumulado {} - {} {}:\n'.format(mes(1), mes(month), year)
    response += "Horas laborables:\t{:.2f}\n".format(labor_hours)
    response += "Horas trabajadas:\t{:.2f}\n".format(worked_hours)
    response += "Horas de diferencia:\t{:.2f}\n".format(
        worked_hours - labor_hours)
    return response


def show_today_summary(login):
    l_hours = count_worked_hours_today(login)
    print("Horas trabajadas hoy:\t{:.2f}\n".format(l_hours))


def accumulated_list_to_csv(login, file_name, month=None, year=None):
    file_path = filename(login, file_name)

    summary = resume_to_string(login, month, year)
    csv_string = accumulated_list_to_csv_string(login, month, year)
    with codecs.open(file_path, 'w', 'utf-8') as out:
        print(summary, file=out)
        print(csv_string, file=out)


def accumulated_list_to_csv_string(login, month=None, year=None):
    """
    listado desde enero hasta el mes indicado
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    mem_file = io.StringIO()
    csv_writer = csv.writer(mem_file, delimiter=',', quotechar='"')
    csv_writer.writerow(('entrada', 'salida', 'horas'))

    for m in range(1, month + 1):
        for line in get_user_attendance_by_month(login, m, year):
            tentry = tlocal(line[0], 'DT')
            texit = tlocal(line[1], 'DT')
            if line[1]:
                hours = line[2]
            else:
                hours = open_session_worked_hours(login)
            csv_writer.writerow((tentry, texit, '{:.2f}'.format(hours)))
    return mem_file.getvalue()


def list_to_csv(login, file_name, month=None, year=None):
    file_path = filename(login, file_name)

    summary = resume_to_string(login, month, year)
    csv_string = list_to_csv_string(login, month, year)
    with codecs.open(file_path, 'w', 'utf-8') as out:
        print(summary, file=out)
        print(csv_string, file=out)


def list_to_csv_string(login, month=None, year=None):
    mem_file = io.StringIO()
    csv_writer = csv.writer(mem_file, delimiter=',', quotechar='"')
    csv_writer.writerow(('entrada', 'salida', 'horas'))
    for line in get_user_attendance_by_month(login, month, year):
        tentry = tlocal(line[0], 'DT')
        texit = tlocal(line[1], 'DT')
        if line[1]:
            hours = line[2]
        else:
            hours = open_session_worked_hours(login)
        csv_writer.writerow((tentry, texit, '{:.2f}'.format(hours)))
    return mem_file.getvalue()


def filename(login, path):
    file_path = Path(path)
    if 'user_email' in login:
        user_name = login['user_email'].split('@')[0]
        file_path = Path(file_path.parents[0],
                         user_name + '-' + file_path.name)
    return file_path


def mail_report_accumulated(login, month=None, year=None):
    mail_report(login, 'accumulated', month, year)


def mail_report_list(login, month=None, year=None):
    mail_report(login, 'list', month, year)


def mail_report(login, mode='list', month=None, year=None):

    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    if 'user_email' in login:
        mail_to = login['user_email']
    else:
        mail_to = tuple(get_mail_users(login, login['uid']))[0]
    user_name = tuple(get_name_users(login, get_user_by_email(login)))[0]
    name = "asistencia{}-{}.csv".format(year, month)
    file_name = filename(login, name)

    if mode == 'accumulated':
        prev_mont = month - 1
        prev_year = year
        if prev_mont == 0:
            prev_mont = 12
            prev_year -= 1
        past_summary = accumulated_summary(login, prev_mont, prev_year)
        current_summary = resume_to_string(login, month, year)
        summary = '{}\n\n{}'.format(current_summary, past_summary)
        csv_table = accumulated_list_to_csv_string(login, month, year)
    else:
        summary = resume_to_string(login, month, year)
        csv_table = list_to_csv_string(login, month, year)

    file_content = summary + csv_table
    subject_tpt = "Informe asistencia {} {}".format(mes(month), year)
    mail_tpt = ''
    mail_tpt_file = os.path.dirname(
        os.path.realpath(__file__)) + '/mail_tpt.txt'
    if Path(mail_tpt_file).is_file():
        with open(mail_tpt_file) as f:
            mail_lines = f.readlines()
            if mail_lines[0][0:9] == "SUBJECT: ":
                subject_tpt = mail_lines[0][9:].rstrip()
                mail_lines.remove(mail_lines[0])
            mail_tpt = ''.join(mail_lines)
    terms = {
        'user_name': user_name,
        'user_email': mail_to,
        'year': year,
        'month': month,
        'month_name': mes(month),
        'filename': file_name,
        'summary': summary,
        'csv_table': csv_table
    }
    body_text = Template(mail_tpt).safe_substitute(terms)
    subject = Template(subject_tpt).safe_substitute(terms)
    send_mail(mail_to, subject, body_text, file_name, file_content)


def list_to_screen(login, month=None, year=None):
    print("Fecha      | Entrada  | Salida   | Horas")

    for line in get_user_attendance_by_month(login, month, year):

        if line[1]:
            print('{} | {} | {} | {:.2f}'.format(
                tlocal(line[0], 'D'),
                tlocal(line[0], 'T'),
                tlocal(line[1], 'T'),
                line[2]))
        else:
            print('{} | {} | {} | {:.2f}'.format(
                tlocal(line[0], 'D'),
                tlocal(line[0], 'T'),
                tlocal(line[1], 'T'),
                open_session_worked_hours(login)))


########################################################################
#
# Holidays, weekends and vacations
#
########################################################################


def public_holidays(login, year):
    """
    Festivos de un año nacionales y provinciales
    """
    user_city = get_state_by_address(login, get_address_id_employee(login))
    holidays = login['conn'].execute_kw(
        login['db'],
        login['uid'],
        login['password'],
        'hr.holidays.public',
        'search_read',
        [[('year', '=', year)]],
        {'fields': ['line_ids']})
    for i in holidays[0]['line_ids']:
        hly = get_holiday(login, i)
        if not hly["state_ids"] or user_city in hly["state_ids"]:
            yield get_holiday(login, i)


def get_holiday(login, id_holiday):
    holidays = login['conn'].execute_kw(
        login['db'],
        login['uid'],
        login['password'],
        'hr.holidays.public.line',
        'search_read',
        [[('id', '=', id_holiday)]],
        {})
    return holidays[0]


@memoize
def holidays_by_month(login, month=None, year=None):
    """
    Listado de festivos
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    for day in public_holidays(login, year):
        if int(day['date'].split('-')[1]) == month:
            yield day['date']


def weekend_days_by_month(month=None, year=None):
    """
    Listado de días correspondientes a fin de semana
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    cal = calendar.Calendar()
    day_list = list(cal.itermonthdays(year, month))
    weekend = day_list[5::7] + day_list[6::7]
    weekend.sort()
    for day in weekend:
        if day != 0:
            yield "{}-{:02d}-{:02d}".format(year, month, day)


@memoize
def get_vacances_by_month(login, month=None, year=None):
    """
    Listado de días de vaciones
    """
    user_id = get_user_id(login)
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    vacances = login['conn'].execute_kw(
        login['db'],
        login['uid'],
        login['password'],
        'hr.holidays',
        'search_read',
        [[]],
        {})
    for i in vacances:
        if i['employee_id'] and i['employee_id'][0] == user_id:
            if i['date_from'] and i['date_to'] and i['state'] != 'refuse':
                d_init = str_to_localtime(i['date_from'])
                d_end = str_to_localtime(i['date_to'])
                if d_init.tm_year == year or d_end.tm_year == year:
                    sdate = date(*d_init[:3])
                    edate = date(*d_end[:3])
                    delta = edate - sdate
                    for inc in range(delta.days + 1):
                        day = sdate + timedelta(days=inc)
                        if day.year == year and day.month == month:
                            yield "{}-{:02d}-{:02d}".format(day.year,
                                                            day.month,
                                                            day.day)


def not_working_by_month(login, month=None, year=None):
    """
    Listado de días no laborables de un mes
    (fiestas + vacaciones + fines de semana)
    """
    not_working = list(set(list(weekend_days_by_month(month, year)) +
                           list(holidays_by_month(login, month, year)) +
                           list(get_vacances_by_month(login, month, year))))
    not_working.sort()
    for day in not_working:
        yield day


########################################################################
#
# Work
#
########################################################################

@memoize
def get_user_attendance_by_month(login, month=None, year=None):
    user_id = get_user_id(login)
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    date_filter = "{}-{:02d}-%".format(year, month)
    try:
        attendance = login['conn'].execute_kw(
            login['db'],
            login['uid'],
            login['password'],
            'hr.attendance',
            'search_read',
            [[('employee_id', '=', user_id),
              ('check_in', '=like', date_filter)]],
            {'fields': ['employee_id', 'check_in', 'check_out',
                        'worked_hours']})
    except TypeError:
        return None
    else:
        for e in attendance:
            yield e['check_in'], e['check_out'], e['worked_hours']


def count_labour_days(login, month=None, year=None):
    """
    Número de días laborables de un mes
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    return calendar.monthrange(year, month)[1] - len(
        list(not_working_by_month(login, month, year)))


def count_labour_days_until_today(login):
    """
    Número de días laborables transcurridos hasta hoy
    """
    days = int(datetime.now().day)
    today = datetime.now().strftime('%Y-%m-%d')

    not_working = 0
    for day in not_working_by_month(login):
        if day <= today:
            not_working += 1
    return days - not_working


def labor_hours_until_today(login):
    """
    Horas laborables transcurridas hasta hoy
    """
    return labor_hours_by_day * count_labour_days_until_today(login)


def total_labor_hours(login, month=None, year=None):
    """
    Horas laborables totales de un mes
    """
    return labor_hours_by_day * count_labour_days(login, month, year)


def count_worked_hours(login, month=None, year=None):
    """
    Horas trabajadas hasta el momento (se cuentan las de las sesión abierta)
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)
    total = 0
    if month == int(datetime.now().month) and year == int(datetime.now().year):
        total = open_session_worked_hours(login)
    for e in get_user_attendance_by_month(login, month, year):
        total += e[2]
    return total


def count_worked_hours_today(login):
    """
    Horas trabajadas hoy (se cuentan las de las sesión abierta)
    """
    today = datetime.now().strftime('%Y-%m-%d')
    total = open_session_worked_hours(login)
    for e in get_user_attendance_by_month(login):
        if e[1] and e[1][0:10] == today:
            total += e[2]
    return total


def open_session_worked_hours(login):
    """
    Horas trasncurridas desde la última sesión abierta y no cerrada
    """
    today = int(datetime.now().day)
    year = int(datetime.now().year)
    month = int(datetime.now().month)
    for e in get_user_attendance_by_month(login, month, year):
        if not e[1] and str_to_localtime(e[0]).tm_mday == today:
            delta = datetime.now() - datetime(*str_to_localtime(e[0])[:6])
            return delta.total_seconds() / 3600
    return 0


########################################################################
#
# Utilities
#
########################################################################

def txt_date(idatetime, mode='DT'):
    if mode == 'T':
        date_format = "%H:%M:%S"
    elif mode == 'D':
        date_format = "%Y-%m-%d"
    else:
        date_format = "%Y-%m-%d %H:%M:%S"

    try:
        txt = time.strftime(date_format, idatetime)
    except TypeError:
        txt = '--------'
    return txt


def str_to_localtime(datetime_str):
    try:
        time_tuple = time.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        gm = calendar.timegm(time_tuple)
    except TypeError:
        return False
    else:
        return time.localtime(gm)


def tlocal(datetime_str, mode='DT'):
    return txt_date(str_to_localtime(datetime_str), mode)


def mes(month):
    """
    Retorna el nombre del mes pasado como argumento
    """
    return ('Enero',
            'Febrero',
            'Marzo',
            'Abril',
            'Mayo',
            'Junio',
            'Julio',
            'Agosto',
            'Septiembre',
            'Octubre',
            'Noviembre',
            'Diciembre')[month - 1]


def get_args_date(month, year):
    if month:
        new_month, new_year = month, year
        if not year:
            year = datetime.now().year
        if month < 0:
            current = int(datetime.now().month)
            result = divmod(current - 1 + month, 12)
            new_month = result[1] + 1
            new_year = year + result[0]
        elif month == 0:
            new_month = None
            new_year = None
        elif 0 < month < 13:
            new_month = month
            new_year = year
        elif args.month > 12:
            sys.exit("Mes fuera de rango")
        return new_month, new_year
    else:
        return month, year


def get_user_id(login):
    """
    Retorna el id en hr.employee del usuario logeado.
    Es un poco ñapa mientras vemos cómo filtrar la query
    """
    user_to_find = get_user_by_email(login) if 'user_email' in login else \
        login['uid']
    if not user_to_find:
        sys.exit('El usuario no existe')
    users = login['conn'].execute_kw(login['db'],
                                     login['uid'],
                                     login['password'],
                                     'hr.employee',
                                     'search_read',
                                     [],
                                     {'fields': ['user_id', 'id']})
    for user in users:
        if user['user_id'][0] == user_to_find:
            return user['id']


def get_user_by_email(login):
    """
    Retorna el id del usaurio (en res.user)
    a partir del email contenido en el campo 'user_email' de login (si lo hay).
    """
    if 'user_email' in login:
        users = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'res.users',
                                         'search_read',
                                         [[('email', '=',
                                            login['user_email'])]],
                                         {'fields': ['email']})
        for user in users:
            return user['id']
    return None


def get_state_by_address(login, address_id):
    """
    Obtiene el código de provicia (state_id) a partir de un address_id
    """
    states = login['conn'].execute_kw(login['db'],
                                      login['uid'],
                                      login['password'],
                                      'res.partner',
                                      'search_read',
                                      [[('id', '=',
                                         address_id)]],
                                      {'fields': ["state_id"]})
    return states[0]["state_id"][0]


def get_address_id_employee(login):
    """
    Obtiene el address_id de un empleado
    """
    user_id = get_user_id(login)
    addresses = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'hr.employee',
                                         'search_read',
                                         [[('id', '=',
                                            user_id)]],
                                         {'fields': ["address_id"]})
    return addresses[0]['address_id'][0]


def get_mail_users(login, user_id=None):
    """
    Retorna los emails de todos los usuarios
    o el de la ID que se le pase
    """
    if user_id:
        users = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'res.users',
                                         'search_read',
                                         [[('id', '=',
                                            user_id)]],
                                         {'fields': ['email']})
    else:
        users = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'res.users',
                                         'search_read',
                                         [],
                                         {'fields': ['email']})
    for user in users:
        yield user['email']


def get_name_users(login, user_id=None):
    """
    Retorna los nombres de todos los usuarios
    o el de la ID que se le pase
    """
    if user_id:
        users = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'res.users',
                                         'search_read',
                                         [[('id', '=',
                                            user_id)]],
                                         {'fields': ['display_name']})
    else:
        users = login['conn'].execute_kw(login['db'],
                                         login['uid'],
                                         login['password'],
                                         'res.users',
                                         'search_read',
                                         [],
                                         {'fields': ['display_name']})
    for user in users:
        yield user['display_name']


def send_mail(mail_to, subject, message, file_name, file_data):
    mail_server = os.environ.get('ODOOCLI_MAIL_SERVER')
    mail_port = os.environ.get('ODOOCLI_MAIL_PORT')
    mail_tls = os.environ.get('ODOOCLI_MAIL_TLS')
    mail_user = os.environ.get('ODOOCLI_MAIL_USER')
    mail_from = os.environ.get('ODOOCLI_MAIL_FROM') or mail_user
    mail_password = os.environ.get('ODOOCLI_MAIL_PASSWORD')
    mail_reply_to = os.environ.get('ODOOCLI_MAIL_REPLY_TO')
    mail_cc = os.environ.get('ODOOCLI_MAIL_CC')
    mail_bcc = os.environ.get('ODOOCLI_MAIL_BCC')

    mail_to_list = [mail_to]

    msg = MIMEMultipart()
    msg['From'] = mail_from
    msg['To'] = mail_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    if mail_cc:
        msg['Cc'] = mail_cc
        mail_to_list.append(mail_cc)
    if mail_bcc:
        mail_to_list.append(mail_bcc)
    if mail_reply_to:
        msg.add_header('reply-to', mail_reply_to)

    msg.attach(MIMEText(message))

    part = MIMEBase('application', "octet-stream")
    part.set_payload(file_data)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
                    'attachment; filename="{}"'.format(file_name))
    msg.attach(part)

    smtp = smtplib.SMTP(mail_server, mail_port)
    if mail_tls:
        smtp.starttls()
    smtp.login(mail_user, mail_password)
    smtp.sendmail(mail_from, mail_to_list, msg.as_string())
    smtp.quit()


def bulk(login, mails, function, *argus):

    if not mails:
        mails = get_mail_users(login)

    for user in mails:
        new_login_data = dict(login)
        new_login_data['user_email'] = user
        if count_worked_hours(new_login_data, argus[-2], argus[-1]):
            print('Procesando', user)
            function(new_login_data, *argus)
        else:
            print('Se omite', user)


########################################################################
#
# Main
#
########################################################################

load_dotenv()

config_file = [
    os.path.dirname(os.path.realpath(__file__)) + '/odoocli.conf']

config_parser = ConfigParser()
config_parser.read(config_file)

if 'ODOOCLIHOST' in os.environ and 'ODOOCLIDATABASE' in os.environ:
    server = os.environ['ODOOCLIHOST']
    db = os.environ['ODOOCLIDATABASE']
elif config_parser.has_option('server', 'host') \
        and config_parser.has_option('server', 'database'):
    server = config_parser.get('server', 'host')
    db = config_parser.get('server', 'database')
else:
    sys.exit('Error en el archivo de configuración')

if __name__ == '__main__':

    help_text = """
Muestra un resumen de la jornada laboral registrada en Odoo hasta el momento,
indicando los días y horas laborables totales del mes, las horas laborables
hasta el día actual y las horas trabajadas hasta el momento (incluídas las
correspondientes a la sesión actual, si es que hay una abierta por el usuario).
"""
    epilog_text = """
Si se indica un mes concreto con la opción --month, se mostrará el resumen
total de ese mes. Se puede concretar el año con la opción --year.

--month admite números negativos. En ese caso, el número se restará del
mes actual, de modo que "-m -1" mostrará el mes anterior al corriente. 

Si se usa el flag --list se mostrará un listado de asistencias en lugar del
resumen.

Con --file NOMBRE_DE ARCHIVO se guarará el listado de asistencias en un archivo
en formato CSV.

Si existen las variables de entorno "ODOOCLIUSER" y "ODOOCLIPASS", se usarán
para el login en Odoo a menos que se indique un usuario con el argumento
--user.

Si existe la variable "ODOOCLIUSER" pero no "ODOOCLIPASS", el programa tomará
el usuario de "ODOOCLIUSER" y mostrará un prompt solicitando la contraseña.

Si tampoco existe la variable "ODOOCLIUSER", se mostrarán sendos prompts
solicitando el nombre de usuario y la contraseña.

Si se usa el argumento --user el programa ignorará las variables de entorno y
mostrará un prompt solicitando la contraseña.
"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=help_text,
        epilog=epilog_text)
    parser.add_argument('-u', '--user', type=str, dest='user',
                        help='Nombre de usuario.\nSi no se aporta se \
                        utilizará el contenido en la variable de entorno \
                        "ODOOCLIUSER"')
    parser.add_argument('-m', '--month', type=int, dest='month',
                        help='Número en el rango [1-12] indicando el mes del \
                        que se mostrará el informe')
    parser.add_argument('-y', '--year', type=int, dest='year',
                        help='Año del que se mostrará el informe.\nSi no se \
                             indica el mes, el valor de este campo será \
                             ignorado')
    parser.add_argument('-f', '--file', type=str,
                        help='Nombre del archivo en el que se guardará un \
                        listado de asistencias (parecido al mostrado con \
                        --list) en formato CSV\nEste argumento hace que se \
                        ignore la opción --list')
    parser.add_argument('-l', '--list', action='count',
                        help='Muestra una lista de asistencias en lugar del \
                             resumen')
    parser.add_argument('-a', '--accumulated', action='count',
                        help='Muestra un resumen de todos los meses desde \
                        enero en lugar del resumen habitual')
    parser.add_argument('-t', '--today', action='count',
                        help='Muestra las horas trabajadas hoy.')
    args = parser.parse_args()

    if args.user:
        username = args.user
        password = getpass.getpass()
    elif os.environ.get('ODOOCLIUSER') and not os.environ.get('ODOOCLIPASS'):
        username = os.environ['ODOOCLIUSER']
        password = getpass.getpass()
    elif os.environ.get('ODOOCLIUSER') and os.environ.get('ODOOCLIPASS'):
        username = os.environ['ODOOCLIUSER']
        password = os.environ['ODOOCLIPASS']
    else:
        username = input('Username: ')
        password = getpass.getpass()

    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(server))
    uid = common.authenticate(db, username, password, {})

    if uid:
        login_data = {'db': db, 'password': password, 'username': username,
                      'uid': uid,
                      'conn': xmlrpc.client.ServerProxy(
                          '{}/xmlrpc/2/object'.format(server))}
    else:
        sys.exit('Error en el Login')

    current_month, current_year = get_args_date(args.month, args.year)

    if args.today:
        show_today_summary(login_data)
    elif args.file:
        if args.accumulated:
            accumulated_list_to_csv(login_data, args.file, current_month,
                                    current_year)
        else:
            list_to_csv(login_data, args.file, current_month, current_year)
    elif args.list:
        if args.month:
            list_to_screen(login_data, current_month, current_year)
        else:
            list_to_screen(login_data)
    else:
        if args.month:
            if args.accumulated:
                year_summary(login_data, current_month, current_year)
            else:
                show_resume(login_data, current_month, current_year)
        else:
            if args.accumulated:
                year_summary(login_data)
            else:
                show_resume_now(login_data)
