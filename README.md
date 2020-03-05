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

Cargará las variables de entorno del archivo `.env`, si es que existe. Esto
puede ser útil para definir las variables "ODOOCLIUSER" y "ODOOCLIPASS".


## Uso

```
odoocli.py [-h] [-u USER] [-m MONTH] [-y YEAR] [-f FILE] [-l]
```

Si se indica un mes concreto con la opción --month, se mostrará el resumen
total de ese mes. Se puede concretar el año con la opción --year.

Si se usa el flag --list se mostrará un listado de asistencias en lugar del
resumen.

Con --file NOMBRE_DE ARCHIVO se guarará el listado de asistencias en un archivo
en formato CSV.

Si existen las variables de entorno "ODOOCLIUSER" y "ODOOCLIPASS", se usarán
para el login en Odoo a menos que se indique un usaurio con el argumento
--user.

Si existe la variable "ODOOCLIUSER" pero no "ODOOCLIPASS", el programa tomará
el usuario de "ODOOCLIUSER" y mostrará un prompt solicitando la contraseña.

Si tampoco existe la variable "ODOOCLIUSER", se mostrarán sendos prompts
solicitando el nombre de usuario y la contraseña.

Si se usa el argumento --user el programa ignorará las variables de entorno y
mostrará un prompt solicitando la contraseña.




