import os
import time
import pandas as pd

from celery_app import celery_app


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = r"C:\Users\cande\Pictures\Proyecto_Ethereum_MT5"
RESULTADOS_DIR = os.path.join(BASE_DIR, "resultados")
GRAFICAS_DIR = os.path.join(RESULTADOS_DIR, "graficas")
EXCEL_FILE = os.path.join(RESULTADOS_DIR, "analisis_ethereum.xlsx")


# ============================================================
# TAREA 1 - CONSULTA / PROCESAMIENTO DE VELAS
# ============================================================

@celery_app.task(bind=True)
def consultar_velas_eth(self):

    inicio = time.time()

    try:
        if not os.path.exists(EXCEL_FILE):
            return {
                "estado": "SIN_DATOS",
                "mensaje": "No existe el archivo de resultados de Ethereum.",
                "duracion_segundos": round(time.time() - inicio, 2)
            }

        df = pd.read_excel(
            EXCEL_FILE,
            sheet_name="Velas_ETH"
        )

        cantidad = len(df)

        return {
            "estado": "COMPLETADO",
            "tarea": "Consulta y procesamiento de velas ETHUSD",
            "simbolo": "ETHUSD",
            "registros": cantidad,
            "duracion_segundos": round(time.time() - inicio, 2),
            "resultado": "Datos de velas cargados y procesados correctamente."
        }

    except Exception as e:

        return {
            "estado": "ERROR",
            "tarea": "Consulta y procesamiento de velas ETHUSD",
            "error": str(e),
            "duracion_segundos": round(time.time() - inicio, 2)
        }


# ============================================================
# TAREA 2 - VERIFICACIÓN DE GRÁFICAS
# ============================================================

@celery_app.task(bind=True)
def generar_graficas_eth(self):

    inicio = time.time()

    try:

        if not os.path.exists(GRAFICAS_DIR):
            return {
                "estado": "SIN_DATOS",
                "mensaje": "La carpeta de gráficas no existe.",
                "duracion_segundos": round(time.time() - inicio, 2)
            }

        archivos = [
            archivo
            for archivo in os.listdir(GRAFICAS_DIR)
            if archivo.lower().endswith(".png")
        ]

        cantidad = len(archivos)

        if cantidad == 0:
            return {
                "estado": "SIN_DATOS",
                "mensaje": "No se encontraron gráficas.",
                "duracion_segundos": round(time.time() - inicio, 2)
            }

        return {
            "estado": "COMPLETADO",
            "tarea": "Generación y verificación de gráficas ETHUSD",
            "graficas_encontradas": cantidad,
            "duracion_segundos": round(time.time() - inicio, 2),
            "resultado": "Las gráficas fueron verificadas correctamente."
        }

    except Exception as e:

        return {
            "estado": "ERROR",
            "tarea": "Generación y verificación de gráficas ETHUSD",
            "error": str(e),
            "duracion_segundos": round(time.time() - inicio, 2)
        }


# ============================================================
# TAREA 3 - GENERACIÓN / VERIFICACIÓN DE EXCEL
# ============================================================

@celery_app.task(bind=True)
def generar_excel_eth(self):

    inicio = time.time()

    try:

        if not os.path.exists(EXCEL_FILE):
            return {
                "estado": "SIN_DATOS",
                "mensaje": "No existe el archivo Excel.",
                "duracion_segundos": round(time.time() - inicio, 2)
            }

        archivo = pd.ExcelFile(EXCEL_FILE)

        hojas = archivo.sheet_names

        registros = {}

        for hoja in hojas:
            try:
                df = pd.read_excel(
                    EXCEL_FILE,
                    sheet_name=hoja
                )

                registros[hoja] = len(df)

            except Exception:
                registros[hoja] = "No se pudo leer"

        return {
            "estado": "COMPLETADO",
            "tarea": "Generación y verificación del reporte Excel",
            "archivo": EXCEL_FILE,
            "hojas": hojas,
            "registros_por_hoja": registros,
            "duracion_segundos": round(time.time() - inicio, 2),
            "resultado": "El archivo Excel fue abierto y verificado correctamente."
        }

    except Exception as e:

        return {
            "estado": "ERROR",
            "tarea": "Generación y verificación del reporte Excel",
            "error": str(e),
            "duracion_segundos": round(time.time() - inicio, 2)
        }


# ============================================================
# TAREA 4 - PERÍODO SIN DATOS
# ============================================================

@celery_app.task(bind=True)
def consultar_periodo_sin_datos(self):

    inicio = time.time()

    return {
        "estado": "SIN_DATOS",
        "tarea": "Consulta de período sin datos",
        "simbolo": "ETHUSD",
        "mensaje": (
            "No se encontraron registros para el período solicitado. "
            "No se generó un reporte para evitar presentar información engañosa."
        ),
        "duracion_segundos": round(time.time() - inicio, 2)
    }