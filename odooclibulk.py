#!/usr/bin/env python3

import argparse
import getpass
import os
import sys
import xmlrpc.client

import odoocli

help_text = """
Hace lo mismo que odoocli.py, pero muestra una serie de informes de los
usuarios solitiados con el argumento --email, en lugar de sólo uno:

Muestra un resumen de la jornada laboral registrada en Odoo hasta el momento,
indicando los días y horas laborables totales del mes, las horas laborables
hasta el día actual y las horas trabajadas hasta el momento (incluídas las
correspondientes a la sesión actual, si es que hay una abierta por el usuario).
"""
epilog_text = """

Si no se indican uno o más correos de usuario con la opción --email se
emitirán informes de todos los usuarios activos.

Si se indica un mes concreto con la opción --month, se mostrará el resumen
total de ese mes. Se puede concretar el año con la opción --year.

--month admite números negativos. En ese caso, el número se restará del
mes actual, de modo que "-m -1" mostrará el mes anterior al corriente. 

Si se usa el flag --list se mostrará un listado de asistencias en lugar del
resumen.

Con --file NOMBRE_DE ARCHIVO se guarará el listado de asistencias en un archivo
en formato CSV por cada usuario. El nombre de cada uno de los archivos creados
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
parser.add_argument('-s', '--send', action='count',
                    help='Envía informes por email')
parser.add_argument('-e', '--email', nargs='*',
                    help='Lista de emails de usuarios sbre los que se \
                         mostrará la información')

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

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(odoocli.server))
uid = common.authenticate(odoocli.db, username, password, {})

if uid:
    login_data = {'db': odoocli.db, 'password': password, 'username': username,
                  'uid': uid,
                  'conn': xmlrpc.client.ServerProxy(
                      '{}/xmlrpc/2/object'.format(odoocli.server))}
else:
    sys.exit('Error en el Login')


if args.email:
    mails = args.email
else:
    mails = None

current_month, current_year = odoocli.get_args_date(args.month, args.year)

if args.file:
    if args.month:
        odoocli.bulk(login_data, mails, odoocli.list_to_csv, args.file,
                     current_month, current_year)
    else:
        odoocli.bulk(login_data, mails, odoocli.list_to_csv, args.file)
elif args.report:
    if args.month:
        odoocli.bulk(login_data, mails, odoocli.mail_report, current_month,
                     current_year)

    else:
        odoocli.bulk(login_data, mails, odoocli.mail_report)
elif args.list:
    if args.month:
        odoocli.bulk(login_data, mails, odoocli.list_to_screen, current_month,
                     current_year)
    else:
        odoocli.bulk(login_data, mails, odoocli.list_to_screen)
else:
    if args.month:
        odoocli.bulk(login_data, mails, odoocli.show_resume, current_month,
                     current_year)
    else:
        odoocli.bulk(login_data, mails, odoocli.show_resume_now)
