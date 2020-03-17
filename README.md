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

Se necesita configurar la URL del servidor de Odoo y el nombre de la base de
datos en el archivo `odoocli.conf`.

Cargará las variables de entorno del archivo `.env` (ver archivo `env.example`),
si es que existe. Esto puede ser útil para definir las variables "ODOOCLIUSER"
y "ODOOCLIPASS".


## Uso

```
odoocli.py [-h] [-u USER] [-m MONTH] [-y YEAR] [-f FILE] [-l]
```

Si se indica un mes concreto con la opción --month, se mostrará el resumen
total de ese mes. Se puede concretar el año con la opción `[-y]`.

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
odooclibulk.py [-h] [-u USER] [-m MONTH] [-y YEAR] [-f FILE] [-l] [-r]
```

Este scrip funciona igual que odoocli.py, pero genera una serie de informes de
todos los usuarios activos, en lugar de sólo un usuario.

Si se usa la opción `[-f FILE]`, se crearán tantos archivos como usuarios activos
haya, con nombres del tipo user-FILE, donde "FILE" es el nombre pasado como argumento
y "user" es el nombre extraído del correo elecrónico del usuario
(la parte de delante de la arroba) 

el argumento `[-r]` enviará un correo electrónicvo a cada usaurio activo con un resumen
del mes indicado (o el mes anterior al corriente, si no se le indica ninguno) y un
listado de asistencias en un archivo adjunto en formato CSV. 

Para la configuración el envío de correos, se usan las siguientes variables de entorno
(ver archivo `env.example`):

* ODOOCLI_MAIL_SERVER
* ODOOCLI_MAIL_PORT
* ODOOCLI_MAIL_TLS
* ODOOCLI_MAIL_USER
* ODOOCLI_MAIL_PASSWORD
* ODOOCLI_MAIL_FROM
