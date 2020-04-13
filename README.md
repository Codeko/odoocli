# odoocli
Informe de tiempos de Odoo

Muestra un resumen de la jornada laboral registrada en Odoo hasta el momento,
indicando los días y horas laborables totales del mes, las horas laborables
hasta el día actual y las horas trabajadas hasta el momento (incluídas las
correspondientes a la sesión actual, si es que hay una abierta por el usaurio).


## Instalación
```
 pip3 install -r requirements.txt
```

Ya no se necesita configurar la URL del servidor de Odoo y el nombre de la base de
datos en el archivo `odoocli.conf`, porque toma esos datos de las variables de
entorno ODOOCLIHOST y ODOOCLIDATABASE respectivamente. Sólo si estas no existen
trata de recurrir a `odoocli.conf` por compatibilidad.

Cargará las variables de entorno del archivo `.env` (ver archivo `env.example`),
si es que existe. Esto puede ser útil para definir las variables "ODOOCLIUSER"
y "ODOOCLIPASS".


## Uso

```
odoocli.py [-h] [-u USER] [-m MONTH] [-y YEAR] [-f FILE] [-l] [-a]
```

Si se indica un mes concreto con la opción `[-m]` `--month`, se mostrará el resumen
total de ese mes. Se puede concretar el año con la opción `[-y]`.

`--month` admite números negativos, que se restrán del mes actual para obtener el
mes del que se emitirá el informe.

El flag `[-a]` hará que se muestre un resumen acumulado desde enero hasta el mes
actual (o hasta le indicado en `[-m]`) en lugar del resumen mensual. 

Si se usa el flag `[-l]` se mostrará un listado de asistencias en lugar del
resumen.

Con `[-f NOMBRE_DE ARCHIVO]` se guarará el listado de asistencias en un archivo
en formato CSV.

Si existen las variables de entorno "ODOOCLIUSER" y "ODOOCLIPASS", se usarán
para el login en Odoo a menos que se indique un usaurio con el argumento
`[-u]`.

Si existe la variable "ODOOCLIUSER" pero no "ODOOCLIPASS", el programa tomará
el usuario de "ODOOCLIUSER" y mostrará un prompt solicitando la contraseña.

Si tampoco existe la variable "ODOOCLIUSER", se mostrarán sendos prompts
solicitando el nombre de usuario y la contraseña.

Si se usa el argumento `[-u]` el programa ignorará las variables de entorno y
mostrará un prompt solicitando la contraseña.


## odooclibulk.py

```
odooclibulk.py [-h] [-u USER] [-m MONTH] [-y YEAR] [-f FILE] [-l] [-s] [-a]
```

Este scrip funciona igual que odoocli.py, pero genera, en lugar de un informe
de un sólo un usuario, una serie de informes de los usaurios indacados con el
argumento --email, que admite una lista de correos electrónicos separados
por espacios.

En caso de que no se asigne ningun correo en --email, se mostrarán todos los
usuarios activos.

Si se usa la opción `[-f FILE]`, se crearán tantos archivos como usuarios haya,
con nombres del tipo user-FILE, donde "FILE" es el nombre pasado como argumento
y "user" es el nombre extraído del correo elecrónico del usuario
(la parte de delante de la arroba) 

El flag `[-s]` enviará un correo electrónico a cada usuario con un resumen
del mes indicado  y un listado de asistencias en un archivo adjunto en formato CSV. 

El argumento `[-e EMAILS]` `--email` permite indicar uno o más correos electrónicos
de usuarios, que serán sobre los que se emita el imforme. 
 
Para la configuración el envío de correos, se usan las siguientes variables de entorno
(ver archivo `env.example`):

* ODOOCLI_MAIL_SERVER
* ODOOCLI_MAIL_PORT
* ODOOCLI_MAIL_TLS
* ODOOCLI_MAIL_USER
* ODOOCLI_MAIL_PASSWORD
* ODOOCLI_MAIL_FROM
* ODOOCLI_MAIL_REPLY_TO
* ODOOCLI_MAIL_CC
* ODOOCLI_MAIL_BCC

La plantilla para el correo elecrónico se encuentra en `mail_tpt.txt`.
Dispone de las siguientes variables para sustituir:

* ${year}
    Año en número
* ${month}
    Mes en número
* ${filename}
    Nombre del fichero CSV
* ${summary}
    Resumen del mes
* ${csv_table}
    Datos de horario en tabla CSV
