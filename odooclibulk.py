#!/usr/bin/python3

import argparse
import getpass
import os
import sys
import xmlrpc.client
from configparser import ConfigParser

from dotenv import load_dotenv

import odoocli

config_file = [os.path.dirname(os.path.realpath(__file__)) + '/odoocli.conf']

load_dotenv()

config_parser = ConfigParser()
config_parser.read(config_file)
if config_parser.has_option('server', 'host') \
        and config_parser.has_option('server', 'database'):
    server = config_parser.get('server', 'host')
    db = config_parser.get('server', 'database')
else:
    sys.exit('Error en el archivo de configuración')

help_text = """
    Hace lo mismo que odoocli.py, pero muestra una serie de informes de todos
    los usuarios, en lugar de sólo uno:

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
    en formato CSV por cada usuario. El nombre de cada uno de los archivos generados
    será "usuario-NOMBRE_DE ARCHIVO", donde "usuario" es el nombre extraído del
    correo electrónico de cada usaurio. 

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
parser.add_argument('-r', '--report', action='count',
                    help='Envía informes por email')

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

if args.month and (args.month < 1 or args.month > 12):
    sys.exit("Mes fuera de rango")
if args.file:
    if args.month:
        if args.year:
            odoocli.bulk(login_data, odoocli.list_to_csv, args.file,
                         args.month, args.year)
        else:
            odoocli.bulk(login_data, odoocli.list_to_csv, args.file,
                         args.month)
    else:
        odoocli.bulk(login_data, odoocli.list_to_csv, args.file)
elif args.report:
    if args.month:
        if args.year:
            odoocli.bulk(login_data, odoocli.mail_report, args.month,
                         args.year)
        else:
            odoocli.bulk(login_data, odoocli.mail_report, args.month)
    else:
        odoocli.bulk(login_data, odoocli.mail_report)
elif args.list:
    if args.month:
        if args.year:
            odoocli.bulk(login_data, odoocli.list_to_screen, args.month,
                         args.year)
        else:
            odoocli.bulk(login_data, odoocli.list_to_screen, args.month)
    else:
        odoocli.bulk(login_data, odoocli.list_to_screen)
else:
    if args.month:
        if args.year:
            odoocli.bulk(login_data, odoocli.show_resume, args.month,
                         args.year)
        else:
            odoocli.bulk(login_data, odoocli.show_resume, args.month)
    else:
        odoocli.bulk(login_data, odoocli.show_resume_now)
