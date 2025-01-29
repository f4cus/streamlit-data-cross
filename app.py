import pandas as pd
import streamlit as st
import time
from io import BytesIO
import zipfile
import plotly.express as px

# Función para mostrar mensajes temporales
def show_temporary_message(message, duration=3):
    """
    Muestra un mensaje temporal en la interfaz de Streamlit.
    El mensaje desaparece después de `duration` segundos.
    """
    placeholder = st.empty()  # Espacio reservado para el mensaje
    placeholder.success(message)  # Mostrar el mensaje
    time.sleep(duration)  # Esperar `duration` segundos
    placeholder.empty()  # Ocultar el mensaje

# 1. Función para cargar datos con manejo de errores y caché
@st.cache_data  # Almacena en caché el resultado de esta función
def load_data():
    """
    Carga los datos desde los archivos CMDB.xlsx y AzureArc.csv.
    Retorna dos DataFrames: df_cmdb y df_arc.
    """
    try:
        # Cargar CMDB.xlsx con parámetros optimizados
        df_cmdb = pd.read_excel(
            "CMDB.xlsx",
            sheet_name="INFRAESTRUCTURA",
            engine="openpyxl",  # Usar openpyxl para archivos .xlsx
            dtype={"Hostname": str}  # Especificar tipos de datos para mejorar la carga
        )
        show_temporary_message("Archivo CMDB.xlsx cargado correctamente.", duration=3)
    except Exception as e:
        st.exception(e)  # Muestra la traza completa del error
        return None, None

    try:
        # Cargar AzureArc.csv con parámetros optimizados
        df_arc = pd.read_csv(
            "AzureArc.csv",
            delimiter=",",
            quotechar='"',
            skipinitialspace=True,
            engine="python",
            dtype={"HOST NAME": str, "NAME": str}  # Especificar tipos de datos para mejorar la carga
        )
        show_temporary_message("Archivo AzureArc.csv cargado correctamente.", duration=3)
    except Exception as e:
        st.exception(e)  # Muestra la traza completa del error
        return None, None

    return df_cmdb, df_arc

# 2. Función para normalizar datos con validaciones
def normalize_data(df_cmdb, df_arc):
    """
    Normaliza las columnas relevantes en ambos DataFrames.
    Retorna los DataFrames normalizados.
    """
    # Validar columnas requeridas en df_cmdb
    if "Hostname" not in df_cmdb.columns:
        st.error("Error: La columna 'Hostname' no existe en CMDB.xlsx.")
        st.stop()

    # Validar columnas requeridas en df_arc
    if "HOST NAME" not in df_arc.columns and "NAME" not in df_arc.columns:
        st.error("Error: No se encuentran las columnas 'HOST NAME' ni 'NAME' en AzureArc.csv.")
        st.stop()

    # Combinar columnas "HOST NAME" y "NAME" en AzureArc.csv
    if "HOST NAME" in df_arc.columns and "NAME" in df_arc.columns:
        df_arc["Hostname_combined"] = df_arc["HOST NAME"].fillna(df_arc["NAME"]).str.strip().str.lower()
    elif "NAME" in df_arc.columns:
        df_arc["Hostname_combined"] = df_arc["NAME"].str.strip().str.lower()

    # Normalizar la columna "Hostname" en CMDB
    df_cmdb["Hostname"] = df_cmdb["Hostname"].str.strip().str.lower()

    # Limpiar valores en ARC AGENT STATUS
    if "ARC AGENT STATUS" in df_arc.columns:
        df_arc["ARC AGENT STATUS"] = df_arc["ARC AGENT STATUS"].astype(str).str.strip()

    return df_cmdb, df_arc

# 3. Función para aplicar filtros preconfigurados
@st.cache_data  # Almacena en caché el resultado de esta función
def apply_filters(df_cmdb):
    """
    Aplica filtros preconfigurados al DataFrame df_cmdb.
    Retorna el DataFrame filtrado.
    """
    try:
        df_cmdb_filtered = df_cmdb[
            (df_cmdb["Familia SO"].str.contains("Windows", case=False, na=False)) &
            (df_cmdb["Capacidad Primaria"].str.contains("Servidor", case=False, na=False))
        ]
        return df_cmdb_filtered
    except KeyError as e:
        st.error(f"Error: No se encontró la columna {e} en CMDB.xlsx.")
        st.stop()

# 4. Función para aplicar filtros dinámicos
def apply_dynamic_filters(df_cmdb_filtered):
    """
    Aplica filtros dinámicos basados en la selección del usuario.
    Retorna el DataFrame filtrado.
    """
    st.sidebar.markdown("### Filtros dinámicos")

    # Filtro por Sistema Operativo
    sistema_operativo_options = df_cmdb_filtered["Sistema operativo"].dropna().unique().tolist()
    sistema_operativo = st.sidebar.multiselect("Seleccionar Sistema Operativo", options=sistema_operativo_options)
    if sistema_operativo:
        df_cmdb_filtered = df_cmdb_filtered[df_cmdb_filtered["Sistema operativo"].isin(sistema_operativo)]

    # Filtro por Estado Operativo
    estado_operativo_options = df_cmdb_filtered["Estado operativo"].dropna().unique().tolist()
    estado_operativo = st.sidebar.multiselect("Seleccionar Estado Operativo", options=estado_operativo_options)
    if estado_operativo:
        df_cmdb_filtered = df_cmdb_filtered[df_cmdb_filtered["Estado operativo"].isin(estado_operativo)]

    # Filtro por Entorno
    entorno_options = df_cmdb_filtered["Entorno"].dropna().unique().tolist()
    entorno = st.sidebar.multiselect("Seleccionar Entorno", options=entorno_options)
    if entorno:
        df_cmdb_filtered = df_cmdb_filtered[df_cmdb_filtered["Entorno"].isin(entorno)]

    # Filtro por Ubicación (excluyente)
    ubicacion_options = df_cmdb_filtered["Ubicación"].dropna().unique().tolist()
    ubicacion_excluir = st.sidebar.multiselect("Seleccionar Ubicaciones a excluir", options=ubicacion_options)
    if ubicacion_excluir:
        df_cmdb_filtered = df_cmdb_filtered[~df_cmdb_filtered["Ubicación"].isin(ubicacion_excluir)]

    # Filtro por Hostname (excluyente)
    hostname_options = df_cmdb_filtered["Hostname"].dropna().unique().tolist()
    hostname_excluir = st.sidebar.multiselect("Seleccionar servidor a excluir", options=hostname_options)
    if hostname_excluir:
        df_cmdb_filtered = df_cmdb_filtered[~df_cmdb_filtered["Hostname"].isin(hostname_excluir)]

    return df_cmdb_filtered

# 5. Función para cruzar datos (merge)
@st.cache_data  # Almacena en caché el resultado de esta función
def merge_data(df_cmdb_filtered, df_arc):
    """
    Realiza el cruce (merge) entre df_cmdb_filtered y df_arc.
    Retorna el DataFrame combinado.
    """
    try:
        df_merged = pd.merge(
            df_cmdb_filtered,
            df_arc,
            left_on="Hostname",
            right_on="Hostname_combined",
            how="left",
            suffixes=("_cmdb", "_arc")
        )
        return df_merged
    except Exception as e:
        st.error(f"Error al realizar el cruce de datos: {e}")
        st.stop()

# 6. Función para exportar datos a Excel
def export_to_excel(df_with_agent, df_without_agent):
    """
    Exporta los DataFrames de "Servidores con agente" y "Servidores sin agente" a un archivo Excel.
    Retorna un objeto BytesIO con el archivo en memoria.
    """
    output = BytesIO()  # Crear un buffer en memoria
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_with_agent.to_excel(writer, sheet_name="Con Agente", index=False)
        df_without_agent.to_excel(writer, sheet_name="Sin Agente", index=False)
    output.seek(0)  # Posicionar el cursor al inicio del buffer
    return output

# 7. Función para exportar datos a CSV
def export_to_csv(df_with_agent, df_without_agent):
    """
    Exporta los DataFrames de "Servidores con agente" y "Servidores sin agente" a un archivo CSV comprimido.
    Retorna un objeto BytesIO con el archivo en memoria.
    """
    output = BytesIO()  # Crear un buffer en memoria
    with zipfile.ZipFile(output, "w") as zipf:
        # Exportar "Servidores con agente" a CSV
        csv_buffer_agent = BytesIO()
        df_with_agent.to_csv(csv_buffer_agent, index=False)
        zipf.writestr("servidores_con_agente.csv", csv_buffer_agent.getvalue())

        # Exportar "Servidores sin agente" a CSV
        csv_buffer_no_agent = BytesIO()
        df_without_agent.to_csv(csv_buffer_no_agent, index=False)
        zipf.writestr("servidores_sin_agente.csv", csv_buffer_no_agent.getvalue())

    output.seek(0)  # Posicionar el cursor al inicio del buffer
    return output

# 8. Función para mostrar resultados
def show_results(df_merged):
    """
    Muestra las métricas y tablas de resultados en la interfaz de Streamlit.
    """
    #Inyectamos CSS personalizado para mejorar visualización
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 55rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    # Identificar servidores con agente
    statuses_with_agent = ["Connected", "Expired", "Offline"]
    df_merged["Tiene_Agente"] = df_merged["ARC AGENT STATUS"].isin(statuses_with_agent)
    with_agent = df_merged["Tiene_Agente"].sum()
    without_agent = len(df_merged) - with_agent
    compliance_percentage = (with_agent / len(df_merged)) * 100 if len(df_merged) > 0 else 0

    # Mostrar métricas principales
    st.markdown("### Resumen General")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de servidores", len(df_merged))
    with col2:
        st.metric("Con agente", with_agent)
    with col3:
        st.metric("Sin agente", without_agent)
    with col4:
        st.metric("Cumplimiento", f"{compliance_percentage:.2f}%")

    # Gráfico de torta para mostrar el porcentaje de servidores con y sin agente
    st.markdown("")
    fig = px.pie(
        values=[with_agent, without_agent],
        names=["Con Agente", "Sin Agente"],
        title="Porcentaje de Servidores con y sin Agente",
        color_discrete_sequence=["#1f77b4","#ff7f0e"]
    )
    fig.update_traces(textfont_size=16)
    st.plotly_chart(fig)

    # Detalle del estado de los agentes
    st.markdown("### Estado de los Servidores con Agente")
    df_merged["ARC AGENT STATUS"] = df_merged["ARC AGENT STATUS"].fillna("No Instalado / No aplica")
    agent_status_counts = df_merged["ARC AGENT STATUS"].value_counts(dropna=False).to_dict()
    df_agent_status = pd.DataFrame.from_dict(agent_status_counts, orient="index", columns=["Cantidad"])
    df_agent_status.index.name = "Status Azure Arc"
    df_agent_status.reset_index(inplace=True)
    df_agent_status = df_agent_status[["Status Azure Arc","Cantidad"]]
    st.dataframe(df_agent_status, hide_index=True, use_container_width=True)

    # Mostrar tablas de detalles una al lado de la otra
    st.markdown("### Detalle de Servidores")
    col1, col2 = st.columns(2)  # Dividir la pantalla en dos columnas

    with col1:
        st.markdown("#### Servidores con Agente")
        df_with_agent = df_merged[df_merged["Tiene_Agente"]].copy()
        df_with_agent["ARC AGENT STATUS"] = df_with_agent["ARC AGENT STATUS"].fillna("No disponible")
        df_with_agent_filtered = df_with_agent[["Hostname", "IP de Administración", "ARC AGENT STATUS"]]
        st.dataframe(df_with_agent_filtered, hide_index=True, use_container_width=True)

    with col2:
        st.markdown("#### Servidores sin Agente")
        df_without_agent = df_merged[~df_merged["Tiene_Agente"]].copy()
        df_without_agent_filtered = df_without_agent[["Hostname", "IP de Administración"]]
        st.dataframe(df_without_agent_filtered, hide_index=True, use_container_width=True)

    # Botón para exportar resultados
    st.markdown("### Exportar Resultados")
    export_format = st.radio("Seleccionar formato de exportación", ("Excel", "CSV"))

    if st.button("Exportar resultados"):
        if export_format == "Excel":
            output = export_to_excel(df_with_agent, df_without_agent)
            st.download_button(
                label="Descargar archivo Excel",
                data=output,
                file_name="resultados_servidores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif export_format == "CSV":
            output = export_to_csv(df_with_agent, df_without_agent)
            st.download_button(
                label="Descargar archivo CSV (ZIP)",
                data=output,
                file_name="resultados_servidores.zip",
                mime="application/zip"
            )

# Flujo principal
def main():
        # Ajustar CSS para evitar que los mensajes se oculten
    st.markdown(
        """
        <style>
        .stAlert {
            z-index: 1000;  # Asegura que los mensajes de error estén en la parte superior
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Cargar datos
    df_cmdb, df_arc = load_data()
    if df_cmdb is None or df_arc is None:
        st.warning("No se pudieron cargar los datos. Por favor, revisa los archivos e intenta nuevamente.")
        return
    st.title("Análisis de Servidores con Azure Arc")
    
    # Normalizar datos
    df_cmdb, df_arc = normalize_data(df_cmdb, df_arc)

    # Aplicar filtros preconfigurados
    df_cmdb_filtered = apply_filters(df_cmdb)

    # Aplicar filtros dinámicos
    df_cmdb_filtered = apply_dynamic_filters(df_cmdb_filtered)

    # Cruce de datos
    df_merged = merge_data(df_cmdb_filtered, df_arc)

    # Mostrar resultados
    show_results(df_merged)

if __name__ == "__main__":
    main()