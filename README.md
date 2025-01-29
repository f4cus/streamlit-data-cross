# streamlit-data-cross
App para análisis y cruce de datos a partir de dos fuentes de datos
-------------------------------------------------------------------

Comparto esta app que me facilitó el cruce de información de dos fuentes de datos y obtener asi un reporte rápido del status de los equipos.
Cómo analista de Ciberseguridad, se me encomendó la tarea de realizar de forma semanal el cruce de información entre la CMDB completa de servidores y un archivo CSV que exportamos a demanda desde Azure ARC, en el cual se reflejan los servidores que reportan a la consola y su estado.
El objetivo: enviar un reporte del cumplimiento de los servidores "elegibles" para que todos cuenten con el agente instalado, activo y actualizado. 
Para los casos de servidores que no aparecen en la consola de Azure Arc, o bien, que aparecen pero su estado es "Offline" o "Expired", se debia gestionar la instalación a actualización del agente.

Esta tarea al ser manual, representaba una gran demanda de trabajo y que provocaba muchas veces errores en los cálculos, por lo cual busqué la forma de mejorar la tarea de cruce de información, dejando atrás las tablas dinámicas en Excel y pasando a un dashboard que contiene filtros dinámicos para obtener el numero preciso segun las caracteristicas y el estado.

¿Cómo probarlo?
En tu máquina, debes tener instalado Python 3.x
1. Crea un entorno virtual:
   python -m venv venv
2. Activa el entorno virtual:
   venv\Scripts\activate
3. Instala las dependencias listadas en el archivo requirements.txt:
   pip install -r requirements.txt
4. Ejecuta Streamlit:
   streamlit run app.py

En este repositorio subi dos fuentes de datos de ejemplo: cmdb.xlsx y AzureArc.csv, deben estar en la misma ubicación de app.py para que pueda leer los datos y hacer el merge.

Con estos dos archivos de ejemplo demostramos el funcionamiento completo:

- Carga de datos.
- Filtros.
- Cruce de información entre CMDB y Azure Arc.
- Identificación de servidores con y sin agente.
- Exportación final de resultados.

Importante:
Para que funcione este código de ejemplo, los archivos a comparar deben contener esta información:

El archivo CMDB.xlsx debe contener una pestaña (sheet) llamada INFRAESTRUCTURA.
El archivo AzureArc.csv debe tener las columnas HOST NAME, NAME y ARC AGENT STATUS.
