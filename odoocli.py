#!/usr/bin/python3
import argparse
import calendar
import codecs
import csv
import getpass
import os
import sys
import time
import xmlrpc.client
from configparser import ConfigParser
from datetime import datetime, date, timedelta
from pathlib import Path

from dotenv import load_dotenv

labor_hours_by_day = 7.0


def show_resume_now(login):
    """
    Informe del mes corriente:
    """
    print("Días laborables de este mes: ", count_labour_days(login))
    print("Horas laborables de este mes: ", total_labor_hours(login))
    print('Horas laborables hasta hoy: ', labor_hours_until_today(login))
    print('Horas trabajadas hasta ahora: ', count_worked_hours(login))


def show_resume(login, month=None, year=None):
    """
    Informe del mes pasado como argumento:
    """
    if year is None:
        year = int(datetime.now().year)
    if month is None:
        month = int(datetime.now().month)

    print(mes(month), year)
    print("Días laborables : ", count_labour_days(login, month, year))
    print("Horas laborables: ", total_labor_hours(login, month, year))
    print('Horas trabajadas: ', count_worked_hours(login, month, year))


def list_to_csv(login, filename, month=None, year=None):
    file_path = Path(filename)
    if 'user_email' in login:
        user_name = login['user_email'].split('@')[0]
        file_path = Path(file_path.parents[0], user_name + '-' + file_path.name)
    with codecs.open(file_path, 'w', 'utf-8') as out:
        csv_writer = csv.writer(out, delimiter=',', quotechar='"')
        csv_writer.writerow(('entrada', 'salida', 'horas'))
        for line in get_user_attendance_by_month(login, month, year):
            tentry = tlocal(line[0], 'DT')
            texit = tlocal(line[1], 'DT')
            if line[1]:
                hours = line[2]
            else:
                hours = open_session_worked_hours(login)

            csv_writer.writerow((tentry, texit, hours))


def list_to_screen(login, month=None, year=None):
    print("Fecha      | Entrada  | Salida   | Horas")

    for line in get_user_attendance_by_month(login, month, year):

        if line[1]:
            print(tlocal(line[0], 'D'), '|',
                  tlocal(line[0], 'T'), '|',
                  tlocal(line[1], 'T'), '|',
                  line[2])
        else:
            print(tlocal(line[0], 'D'), '|',
                  tlocal(line[0], 'T'), '|',
                  tlocal(line[1], 'T'), '|',
                  '(' + str(open_session_worked_hours(login)) + ')')


########################################################################
#
# Holidays, weekends and vacations
#
########################################################################


def public_holidays(login, year):
    """
    Festivos de un año
    """
    holidays = login['conn'].execute_kw(
        login['db'],
        login['uid'],
        login['password'],
        'hr.holidays.public',
        'search_read',
        [[('year', '=', year)]],
        {'fields': ['line_ids']})
    for i in holidays[0]['line_ids']:
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
            [[('employee_id', '=', user_id), ('check_in', '=like', date_filter)]],
            {'fields': ['employee_id', 'check_in', 'check_out', 'worked_hours']})
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
    return calendar.monthrange(year, month)[1] - len(list(not_working_by_month(login, month, year)))


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


def get_user_id(login):
    """
    Retorna el id en hr.employee del usuario logeado.
    Es un poco ñapa mientras vemos cómo filtrar la query
    """
    user_to_find = get_user_by_email(login) if 'user_email' in login else login['uid']
    if not user_to_find:
        sys.exit('El usaurio no existe')
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
                                         [[('email', '=', login['user_email'])]],
                                         {'fields': ['email']})
        for user in users:
            return user['id']
    return None


def get_mail_users(login):
    """
    Retorna los emails de todos los usuarios
    """
    users = login['conn'].execute_kw(login['db'],
                                     login['uid'],
                                     login['password'],
                                     'res.users',
                                     'search_read',
                                     [],
                                     {'fields': ['email']})
    for user in users:
        yield user['email']


def bulk(login, function, *argus):
    for user in get_mail_users(login):
        new_login_data = dict(login)
        new_login_data['user_email'] = user
        if count_worked_hours(new_login_data):
            print('Procesando', user)
            function(new_login_data, *argus)
        else:
            print('Se omite', user)


########################################################################
#
# Main
#
########################################################################

if __name__ == '__main__':

    config_file = [os.path.dirname(os.path.realpath(__file__)) + '/odoocli.conf']

    help_text = """
    Muestra un resumen de la jornada laboral registrada en Odoo hasta el momento,
    indicando los días y horas laborables totales del mes, las horas laborables
    hasta el día actual y las horas trabajadas hasta el momento (incluídas las
    correspondientes a la sesión actual, si es que hay una abierta por el usuario).
    """
    epilog_text = """
    Si se indica un mes concreto con la opción --month, se mostrará el resumen
    total de ese mes. Se puede concretar el año con la opción --year.

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

    load_dotenv()

    config_parser = ConfigParser()
    config_parser.read(config_file)
    if config_parser.has_option('server', 'host') \
            and config_parser.has_option('server', 'database'):
        server = config_parser.get('server', 'host')
        db = config_parser.get('server', 'database')
    else:
        sys.exit('Error en el archivo de configuración')

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=help_text,
        epilog=epilog_text)
    parser.add_argument('-u', '--user', type=str, dest='user',
                        help='Nombre de usuario.\nSi no se aporta se utilizará el \
                             contenido en la variable de entorno "ODOOCLIUSER"')
    parser.add_argument('-m', '--month', type=int, dest='month',
                        help='Número en el rango [1-12] indicando el mes del que \
                             se mostrará el informe')
    parser.add_argument('-y', '--year', type=int, dest='year',
                        help='Año del que se mostrará el informe.\nSi no se \
                             indica el mes, el valor de este campo será ignorado')
    parser.add_argument('-f', '--file', type=str,
                        help='Nombre del archivo en el que se guardará un listado \
                             de asistencias (parecido al mostrado con --list) en \
                             formato CSV\nEste argumento hace que se ignore la \
                             opción --list')
    parser.add_argument('-l', '--list', action='count',
                        help='Muestra una lista de asistencias en lugar del \
                             resumen')
    parser.add_argument('-e', '--email', type=str, dest='email',
                        help='eMail del usuario del que se generará el informe')
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
        login_data = {'db': db, 'password': password, 'username': username, 'uid': uid,
                      'conn': xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(server))}
        if args.email:
            login_data['user_email'] = args.email
    else:
        sys.exit('Error en el Login')

    if args.month and (args.month < 1 or args.month > 12):
        sys.exit("Mes fuera de rango")
    if args.file:
        if args.month:
            if args.year:
                list_to_csv(login_data, args.file, args.month, args.year)
            else:
                list_to_csv(login_data, args.file, args.month)
        else:
            list_to_csv(login_data, args.file)
    elif args.list:
        if args.month:
            if args.year:
                list_to_screen(login_data, args.month, args.year)
            else:
                list_to_screen(login_data, args.month)
        else:
            list_to_screen(login_data)
    else:
        if args.month:
            if args.year:
                show_resume(login_data, args.month, args.year)
            else:
                show_resume(login_data, args.month)
        else:
            show_resume_now(login_data)
