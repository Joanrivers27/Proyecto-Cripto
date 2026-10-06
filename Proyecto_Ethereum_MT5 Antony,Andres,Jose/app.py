import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timezone, timedelta
from pathlib import Path
import time
import sys
import traceback


# ============================================================
# INTEGRACIÓN CON CELERY
# ============================================================

CELERY_DISPONIBLE = False
CELERY_ERROR = ""

try:
    from tasks import (
        consultar_velas_eth,
        generar_graficas_eth,
        generar_excel_eth,
        consultar_periodo_sin_datos
    )

    CELERY_DISPONIBLE = True

except Exception as error:
    CELERY_DISPONIBLE = False
    CELERY_ERROR = str(error)

# ============================================================
# CONFIGURACIÓN
# ============================================================

SIMBOLO = "ETHUSD"
TIMEFRAME = mt5.TIMEFRAME_H1

DIAS_ANALISIS = 7
DIAS_EXTENDIDOS = 28

BASE = Path(r"C:\Users\cande\Pictures\Proyecto_Ethereum_MT5")
RESULTADOS = BASE / "resultados"
GRAFICAS = RESULTADOS / "graficas"

EXCEL = RESULTADOS / "analisis_ethereum.xlsx"
INFORME = RESULTADOS / "informe_visual.md"

RESULTADOS.mkdir(parents=True, exist_ok=True)
GRAFICAS.mkdir(parents=True, exist_ok=True)


# ============================================================
# FUNCIONES GENERALES
# ============================================================

def ahora_utc():
    return datetime.now(timezone.utc)


def fecha_texto(fecha):
    if pd.isna(fecha):
        return ""
    if not isinstance(fecha, pd.Timestamp):
        fecha = pd.Timestamp(fecha)

    if fecha.tzinfo is None:
        fecha = fecha.tz_localize("UTC")

    return fecha.strftime("%Y-%m-%d %H:%M:%S UTC")


def quitar_zona(df):
    """
    Excel no permite datetimes con timezone.
    Se elimina la zona solamente para guardar en Excel.
    Los datos siguen representándose como UTC.
    """
    copia = df.copy()

    for columna in copia.columns:
        if pd.api.types.is_datetime64_any_dtype(copia[columna]):
            try:
                if copia[columna].dt.tz is not None:
                    copia[columna] = copia[columna].dt.tz_localize(None)
            except Exception:
                pass

    return copia


def guardar_grafica(nombre):
    ruta = GRAFICAS / nombre
    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()
    return ruta


def preparar_velas(rates):
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)

    df["fecha_utc"] = pd.to_datetime(
        df["time"],
        unit="s",
        utc=True
    )

    df = df.rename(columns={
        "open": "apertura",
        "high": "maximo",
        "low": "minimo",
        "close": "cierre",
        "tick_volume": "volumen_ticks",
        "spread": "spread",
        "real_volume": "volumen_real"
    })

    columnas = [
        "fecha_utc",
        "apertura",
        "maximo",
        "minimo",
        "cierre",
        "volumen_ticks",
        "spread",
        "volumen_real"
    ]

    df = df[[c for c in columnas if c in df.columns]].copy()

    df = df.sort_values("fecha_utc").reset_index(drop=True)

    df["rango_usd"] = df["maximo"] - df["minimo"]

    df["cambio_pct"] = df["cierre"].pct_change() * 100

    df["movimiento_abs_pct"] = df["cambio_pct"].abs()

    df["tipo_vela"] = np.select(
        [
            df["cierre"] > df["apertura"],
            df["cierre"] < df["apertura"]
        ],
        [
            "Alcista",
            "Bajista"
        ],
        default="Sin cambio"
    )

    return df


def obtener_velas(desde, hasta):
    rates = mt5.copy_rates_range(
        SIMBOLO,
        TIMEFRAME,
        desde,
        hasta
    )

    if rates is None:
        return pd.DataFrame()

    return preparar_velas(rates)


def obtener_ultimas_velas(cantidad=100):
    rates = mt5.copy_rates_from_pos(
        SIMBOLO,
        TIMEFRAME,
        1,
        cantidad
    )

    if rates is None:
        return pd.DataFrame()

    return preparar_velas(rates)


def comprobar_mt5():
    print("=" * 70)
    print("INICIANDO META TRADER 5")
    print("=" * 70)

    if not mt5.initialize():
        print("ERROR: No se pudo conectar con MetaTrader 5")
        print("Código:", mt5.last_error())
        return False

    print("MT5 conectado correctamente.")

    simbolo_info = mt5.symbol_info(SIMBOLO)

    if simbolo_info is None:
        print(f"ERROR: No existe el símbolo {SIMBOLO}")
        print("Código:", mt5.last_error())
        return False

    if not simbolo_info.visible:
        if not mt5.symbol_select(SIMBOLO, True):
            print(f"ERROR: No se pudo seleccionar {SIMBOLO}")
            return False

    return True


# ============================================================
# ACTIVIDAD 1
# IDENTIFICACIÓN DEL INSTRUMENTO
# ============================================================

def actividad_1(info):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 1 - IDENTIFICACIÓN DEL INSTRUMENTO")
    print("=" * 70)

    resultado = {
        "Simbolo": SIMBOLO,
        "Descripcion": info.description,
        "Moneda_base": info.currency_base,
        "Moneda_ganancia": info.currency_profit,
        "Digitos": info.digits,
        "Tamano_contrato": info.trade_contract_size
    }

    for clave, valor in resultado.items():
        print(f"{clave}: {valor}")

    return resultado


# ============================================================
# ACTIVIDAD 2
# BID / ASK / SPREAD
# ============================================================

def actividad_2(info):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 2 - BID / ASK / SPREAD")
    print("=" * 70)

    tick = mt5.symbol_info_tick(SIMBOLO)

    if tick is None:
        print("No se pudo obtener el tick actual.")
        return {}

    bid = float(tick.bid)
    ask = float(tick.ask)
    spread = ask - bid

    timestamp = datetime.fromtimestamp(
        tick.time,
        tz=timezone.utc
    )

    resultado = {
        "Bid_USD": bid,
        "Ask_USD": ask,
        "Spread_USD": spread,
        "Fecha_UTC": fecha_texto(timestamp)
    }

    for clave, valor in resultado.items():
        print(f"{clave}: {valor}")

    return resultado


# ============================================================
# ACTIVIDAD 3
# ÚLTIMAS 100 VELAS
# ============================================================

def actividad_3():
    print("\n" + "=" * 70)
    print("ACTIVIDAD 3 - ÚLTIMAS 100 VELAS HORARIAS")
    print("=" * 70)

    df = obtener_ultimas_velas(100)

    if df.empty:
        print("No se encontraron velas.")
        return df

    print("Columnas:")
    print(df.columns.tolist())

    print("\nHEAD:")
    print(df.head())

    print("\nTAIL:")
    print(df.tail())

    print(f"\nRegistros: {len(df)}")

    return df


# ============================================================
# ACTIVIDAD 4
# SIETE DÍAS
# ============================================================

def actividad_4():
    print("\n" + "=" * 70)
    print("ACTIVIDAD 4 - SIETE DÍAS DE VELAS HORARIAS")
    print("=" * 70)

    hasta = ahora_utc()
    desde = hasta - timedelta(days=DIAS_ANALISIS)

    df = obtener_velas(desde, hasta)

    print("Periodo solicitado:")
    print(fecha_texto(desde))
    print("hasta")
    print(fecha_texto(hasta))

    if df.empty:
        print("No se encontraron datos.")
        return df

    print("\nPeriodo real:")
    print(fecha_texto(df["fecha_utc"].min()))
    print("hasta")
    print(fecha_texto(df["fecha_utc"].max()))

    print(f"\nRegistros encontrados: {len(df)}")

    return df


# ============================================================
# ACTIVIDAD 5
# CALIDAD DE DATOS
# ============================================================

def actividad_5(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 5 - CALIDAD DE DATOS")
    print("=" * 70)

    faltantes = df.isna().sum()

    duplicadas = df["fecha_utc"].duplicated().sum()

    diferencias = df["fecha_utc"].diff().dropna()

    intervalos_anormales = (
        diferencias != pd.Timedelta(hours=1)
    ).sum()

    print("\nValores faltantes:")
    print(faltantes)

    print("\nFechas duplicadas:", duplicadas)
    print("Intervalos horarios anormales:", intervalos_anormales)

    calidad = pd.DataFrame({
        "indicador": [
            "Valores faltantes",
            "Fechas duplicadas",
            "Intervalos horarios anormales"
        ],
        "valor": [
            int(faltantes.sum()),
            int(duplicadas),
            int(intervalos_anormales)
        ]
    })

    return calidad


# ============================================================
# ACTIVIDAD 6
# GRÁFICA DE CIERRE
# ============================================================

def actividad_6(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 6 - PRECIO DE CIERRE")
    print("=" * 70)

    maximo = df.loc[df["cierre"].idxmax()]
    minimo = df.loc[df["cierre"].idxmin()]

    print(
        f"Máximo: {maximo['cierre']:.2f} USD "
        f"({fecha_texto(maximo['fecha_utc'])})"
    )

    print(
        f"Mínimo: {minimo['cierre']:.2f} USD "
        f"({fecha_texto(minimo['fecha_utc'])})"
    )

    plt.figure(figsize=(13, 6))
    plt.plot(df["fecha_utc"], df["cierre"], label="Cierre")

    plt.scatter(
        maximo["fecha_utc"],
        maximo["cierre"],
        marker="o",
        s=70,
        label="Máximo"
    )

    plt.scatter(
        minimo["fecha_utc"],
        minimo["cierre"],
        marker="o",
        s=70,
        label="Mínimo"
    )

    plt.title(
        f"{SIMBOLO} - Precio de cierre horario\n"
        f"Periodo: {fecha_texto(df['fecha_utc'].min())} "
        f"a {fecha_texto(df['fecha_utc'].max())}"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Precio de cierre (USD)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(rotation=45)

    guardar_grafica("06_cierre_7_dias.png")

    return {
        "maximo": maximo,
        "minimo": minimo
    }


# ============================================================
# ACTIVIDAD 7
# MAYORES RANGOS
# ============================================================

def actividad_7(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 7 - 10 MAYORES RANGOS")
    print("=" * 70)

    top = df.nlargest(10, "rango_usd").copy()

    print(
        top[
            [
                "fecha_utc",
                "maximo",
                "minimo",
                "rango_usd"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    etiquetas = top["fecha_utc"].dt.strftime("%m-%d %H:%M")

    plt.bar(
        etiquetas,
        top["rango_usd"]
    )

    plt.title("10 mayores rangos horarios de ETHUSD")
    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Rango de la vela (USD)")
    plt.xticks(rotation=45)
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("07_mayores_rangos.png")

    return top


# ============================================================
# ACTIVIDAD 8
# MAYORES SUBIDAS
# ============================================================

def actividad_8(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 8 - 10 MAYORES SUBIDAS HORARIAS")
    print("=" * 70)

    top = df.nlargest(10, "cambio_pct").copy()

    print(
        top[
            [
                "fecha_utc",
                "cierre",
                "cambio_pct"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    etiquetas = top["fecha_utc"].dt.strftime("%m-%d %H:%M")

    plt.bar(
        etiquetas,
        top["cambio_pct"]
    )

    plt.title("10 mayores subidas horarias de ETHUSD")
    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Variación horaria (%)")
    plt.xticks(rotation=45)
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("08_mayores_subidas.png")

    return top


# ============================================================
# ACTIVIDAD 9
# MAYORES BAJADAS
# ============================================================

def actividad_9(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 9 - 10 MAYORES BAJADAS HORARIAS")
    print("=" * 70)

    top = df.nsmallest(10, "cambio_pct").copy()

    print(
        top[
            [
                "fecha_utc",
                "cierre",
                "cambio_pct"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    etiquetas = top["fecha_utc"].dt.strftime("%m-%d %H:%M")

    plt.bar(
        etiquetas,
        top["cambio_pct"]
    )

    plt.title("10 mayores bajadas horarias de ETHUSD")
    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Variación horaria (%)")
    plt.xticks(rotation=45)
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("09_mayores_bajadas.png")

    return top


# ============================================================
# ACTIVIDAD 10
# ALCISTAS / BAJISTAS
# ============================================================

def actividad_10(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 10 - TIPO DE VELA")
    print("=" * 70)

    conteo = df["tipo_vela"].value_counts()

    total = len(df)

    resumen = pd.DataFrame({
        "tipo": conteo.index,
        "cantidad": conteo.values
    })

    resumen["proporcion_pct"] = (
        resumen["cantidad"] / total * 100
    )

    print(resumen.to_string(index=False))

    plt.figure(figsize=(9, 6))

    plt.bar(
        resumen["tipo"],
        resumen["cantidad"]
    )

    plt.title("Velas alcistas, bajistas y sin cambio")
    plt.xlabel("Tipo de vela")
    plt.ylabel("Cantidad")
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("10_tipo_velas.png")

    return resumen


# ============================================================
# ACTIVIDAD 11
# RESUMEN DIARIO
# ============================================================

def actividad_11(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 11 - RESUMEN DIARIO")
    print("=" * 70)

    diario = (
        df.set_index("fecha_utc")
        .resample("1D")
        .agg(
            apertura=("apertura", "first"),
            maximo=("maximo", "max"),
            minimo=("minimo", "min"),
            cierre=("cierre", "last"),
            volumen_ticks=("volumen_ticks", "sum")
        )
        .reset_index()
    )

    diario["rango_usd"] = (
        diario["maximo"] - diario["minimo"]
    )

    diario["cambio_pct"] = (
        diario["cierre"].pct_change() * 100
    )

    print(diario.to_string(index=False))

    plt.figure(figsize=(12, 6))

    plt.plot(
        diario["fecha_utc"],
        diario["cierre"],
        marker="o"
    )

    plt.title("Precio de cierre diario de ETHUSD")
    plt.xlabel("Fecha UTC")
    plt.ylabel("Cierre (USD)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    guardar_grafica("11_cierres_diarios.png")

    return diario


# ============================================================
# ACTIVIDAD 12
# MEJOR / PEOR DÍA
# ============================================================

def actividad_12(diario):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 12 - COMPARACIÓN DE DÍAS")
    print("=" * 70)

    valido = diario.dropna(subset=["cambio_pct"])

    mayor_subida = valido.loc[
        valido["cambio_pct"].idxmax()
    ]

    mayor_bajada = valido.loc[
        valido["cambio_pct"].idxmin()
    ]

    mayor_rango = diario.loc[
        diario["rango_usd"].idxmax()
    ]

    print(
        "Mayor subida:",
        fecha_texto(mayor_subida["fecha_utc"]),
        f"{mayor_subida['cambio_pct']:.6f}%"
    )

    print(
        "Mayor bajada:",
        fecha_texto(mayor_bajada["fecha_utc"]),
        f"{mayor_bajada['cambio_pct']:.6f}%"
    )

    print(
        "Mayor rango:",
        fecha_texto(mayor_rango["fecha_utc"]),
        f"{mayor_rango['rango_usd']:.2f} USD"
    )

    return pd.DataFrame([
        mayor_subida,
        mayor_bajada,
        mayor_rango
    ])


# ============================================================
# ACTIVIDAD 13
# MOVIMIENTO POR HORA UTC
# ============================================================

def actividad_13(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 13 - MOVIMIENTO POR HORA UTC")
    print("=" * 70)

    resumen = (
        df.dropna(subset=["movimiento_abs_pct"])
        .assign(hora=lambda x: x["fecha_utc"].dt.hour)
        .groupby("hora")["movimiento_abs_pct"]
        .mean()
        .reset_index()
    )

    resumen.columns = [
        "hora_utc",
        "movimiento_promedio_pct"
    ]

    print(resumen.to_string(index=False))

    plt.figure(figsize=(11, 6))

    plt.plot(
        resumen["hora_utc"],
        resumen["movimiento_promedio_pct"],
        marker="o"
    )

    plt.title("Movimiento promedio por hora UTC")
    plt.xlabel("Hora UTC")
    plt.ylabel("Movimiento absoluto promedio (%)")
    plt.grid(True, alpha=0.3)

    guardar_grafica("13_movimiento_hora.png")

    return resumen


# ============================================================
# ACTIVIDAD 14
# DÍA DE LA SEMANA
# ============================================================

def actividad_14(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 14 - MOVIMIENTO POR DÍA")
    print("=" * 70)

    nombres = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo"
    }

    resumen = (
        df.dropna(subset=["movimiento_abs_pct"])
        .assign(
            dia_num=lambda x: x["fecha_utc"].dt.dayofweek
        )
        .groupby("dia_num")["movimiento_abs_pct"]
        .mean()
        .reset_index()
    )

    resumen["dia"] = resumen["dia_num"].map(nombres)

    resumen = resumen.sort_values("dia_num")

    print(
        resumen[
            ["dia", "movimiento_abs_pct"]
        ].to_string(index=False)
    )

    plt.figure(figsize=(10, 6))

    plt.bar(
        resumen["dia"],
        resumen["movimiento_abs_pct"]
    )

    plt.title("Movimiento horario promedio por día")
    plt.xlabel("Día de la semana")
    plt.ylabel("Movimiento absoluto promedio (%)")
    plt.xticks(rotation=30)
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("14_movimiento_dia.png")

    return resumen


# ============================================================
# ACTIVIDAD 15
# MEDIA MÓVIL 20 HORAS
# ============================================================

def actividad_15(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 15 - MEDIA MÓVIL DE 20 HORAS")
    print("=" * 70)

    datos = df.copy()

    datos["media_20h"] = (
        datos["cierre"]
        .rolling(20)
        .mean()
    )

    datos["arriba_media"] = (
        datos["cierre"] > datos["media_20h"]
    )

    cruces = datos["arriba_media"].ne(
        datos["arriba_media"].shift()
    )

    cruces = datos[cruces].dropna(
        subset=["media_20h"]
    )

    print(
        "Cruces encontrados:",
        len(cruces)
    )

    print(
        cruces[
            [
                "fecha_utc",
                "cierre",
                "media_20h"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    plt.plot(
        datos["fecha_utc"],
        datos["cierre"],
        label="Cierre"
    )

    plt.plot(
        datos["fecha_utc"],
        datos["media_20h"],
        label="Media móvil 20h"
    )

    plt.title("ETHUSD - Cierre y media móvil de 20 horas")
    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Precio (USD)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(rotation=45)

    guardar_grafica("15_media_movil_20h.png")

    return datos, cruces


# ============================================================
# ACTIVIDAD 16
# ALTA VARIACIÓN
# ============================================================

def actividad_16(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 16 - ALTA VARIACIÓN")
    print("=" * 70)

    percentil = (
        df["movimiento_abs_pct"]
        .dropna()
        .quantile(0.90)
    )

    top = (
        df[
            df["movimiento_abs_pct"] >= percentil
        ]
        .nlargest(10, "movimiento_abs_pct")
        .copy()
    )

    print(
        f"Criterio: movimiento absoluto >= "
        f"{percentil:.4f}%"
    )

    print(
        top[
            [
                "fecha_utc",
                "cambio_pct",
                "movimiento_abs_pct"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    plt.plot(
        df["fecha_utc"],
        df["cierre"],
        label="Cierre"
    )

    plt.scatter(
        top["fecha_utc"],
        top["cierre"],
        s=70,
        label="Alta variación"
    )

    plt.title(
        "ETHUSD - Periodos de alta variación"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Precio de cierre (USD)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xticks(rotation=45)

    guardar_grafica("16_alta_variacion.png")

    return top, percentil


# ============================================================
# ACTIVIDAD 17
# TICK VOLUME
# ============================================================

def actividad_17(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 17 - MAYOR TICK VOLUME")
    print("=" * 70)

    top = df.nlargest(
        10,
        "volumen_ticks"
    ).copy()

    print(
        top[
            [
                "fecha_utc",
                "cierre",
                "volumen_ticks"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    plt.bar(
        top["fecha_utc"].dt.strftime("%m-%d %H:%M"),
        top["volumen_ticks"]
    )

    plt.title("10 mayores tick volumes de ETHUSD")
    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Tick volume")
    plt.xticks(rotation=45)
    plt.grid(axis="y", alpha=0.3)

    guardar_grafica("17_tick_volume.png")

    print(
        "\nNota: tick volume representa cambios de cotización "
        "registrados por el proveedor y no equivale necesariamente "
        "al volumen total negociado de Ethereum."
    )

    return top


# ============================================================
# ACTIVIDAD 18
# HORARIO VS DIARIO
# ============================================================

def actividad_18(df, diario):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 18 - HORARIO VS DIARIO")
    print("=" * 70)

    print(
        "Registros horarios:",
        len(df)
    )

    print(
        "Registros diarios:",
        len(diario)
    )

    print(
        "Rango horario:",
        f"{df['minimo'].min():.2f} - "
        f"{df['maximo'].max():.2f} USD"
    )

    print(
        "Rango diario:",
        f"{diario['minimo'].min():.2f} - "
        f"{diario['maximo'].max():.2f} USD"
    )

    plt.figure(figsize=(13, 6))

    plt.plot(
        df["fecha_utc"],
        df["cierre"]
    )

    plt.title(
        "ETHUSD - Tendencia horaria"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Precio de cierre (USD)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    guardar_grafica("18_horario_vs_diario.png")

    return {
        "horario": len(df),
        "diario": len(diario)
    }


# ============================================================
# ACTIVIDAD 19
# CONTROL DE PROCESAMIENTO SIN CELERY
# ============================================================

def actividad_19(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 19 - CONTROL DE CONSULTA Y REPORTE")
    print("=" * 70)

    inicio = time.perf_counter()

    resultado = {
        "tarea": "Consulta y generación del análisis ETHUSD",
        "estado": "COMPLETADO",
        "simbolo": SIMBOLO,
        "registros": len(df)
    }

    duracion = time.perf_counter() - inicio

    resultado["duracion_segundos"] = round(
        duracion,
        4
    )

    print(resultado)

    return pd.DataFrame([resultado])


# ============================================================
# ACTIVIDAD 20
# EXCEL BASE
# ============================================================

def actividad_20(
    df,
    df100,
    diario,
    mayores_rangos,
    calidad,
    metadatos,
    alcistas_bajistas,
    movimiento_hora,
    movimiento_dia,
    alta_variacion,
    tick_volume
):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 20 - GENERACIÓN Y VERIFICACIÓN DEL EXCEL")
    print("=" * 70)

    with pd.ExcelWriter(
        EXCEL,
        engine="openpyxl"
    ) as writer:

        quitar_zona(df).to_excel(
            writer,
            sheet_name="Velas_ETH",
            index=False
        )

        quitar_zona(df100).to_excel(
            writer,
            sheet_name="Ultimas_100",
            index=False
        )

        quitar_zona(diario).to_excel(
            writer,
            sheet_name="Resumen_diario",
            index=False
        )

        quitar_zona(mayores_rangos).to_excel(
            writer,
            sheet_name="Mayores_movimientos",
            index=False
        )

        calidad.to_excel(
            writer,
            sheet_name="Calidad",
            index=False
        )

        metadatos.to_excel(
            writer,
            sheet_name="Metadatos",
            index=False
        )

        alcistas_bajistas.to_excel(
            writer,
            sheet_name="Velas_alcistas",
            index=False
        )

        movimiento_hora.to_excel(
            writer,
            sheet_name="Movimiento_hora",
            index=False
        )

        movimiento_dia.to_excel(
            writer,
            sheet_name="Movimiento_dia",
            index=False
        )

        quitar_zona(alta_variacion).to_excel(
            writer,
            sheet_name="Alta_variacion",
            index=False
        )

        quitar_zona(tick_volume).to_excel(
            writer,
            sheet_name="Tick_volume",
            index=False
        )

    excel = pd.ExcelFile(EXCEL)

    print("Archivo:", EXCEL)
    print("Hojas:")
    print(excel.sheet_names)

    return excel.sheet_names


# ============================================================
# ACTIVIDAD 21
# CAMBIO ACUMULADO
# ============================================================

def actividad_21(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 21 - CAMBIO ACUMULADO")
    print("=" * 70)

    datos = df.copy()

    primer_cierre = datos["cierre"].iloc[0]

    datos["cambio_acumulado_pct"] = (
        (datos["cierre"] / primer_cierre - 1)
        * 100
    )

    maximo = datos.loc[
        datos["cambio_acumulado_pct"].idxmax()
    ]

    minimo = datos.loc[
        datos["cambio_acumulado_pct"].idxmin()
    ]

    print(
        f"Máximo acumulado: "
        f"{maximo['cambio_acumulado_pct']:.4f}% "
        f"en {fecha_texto(maximo['fecha_utc'])}"
    )

    print(
        f"Mínimo acumulado: "
        f"{minimo['cambio_acumulado_pct']:.4f}% "
        f"en {fecha_texto(minimo['fecha_utc'])}"
    )

    plt.figure(figsize=(13, 6))

    plt.plot(
        datos["fecha_utc"],
        datos["cambio_acumulado_pct"]
    )

    plt.axhline(
        0,
        linestyle="--"
    )

    plt.title(
        "ETHUSD - Cambio porcentual acumulado"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Cambio acumulado (%)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    guardar_grafica("21_cambio_acumulado.png")

    return datos[
        [
            "fecha_utc",
            "cierre",
            "cambio_acumulado_pct"
        ]
    ]


# ============================================================
# ACTIVIDAD 22
# RACHAS ALCISTAS / BAJISTAS
# ============================================================

def actividad_22(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 22 - RACHAS ALCISTAS Y BAJISTAS")
    print("=" * 70)

    datos = df.reset_index(drop=True).copy()

    rachas = []

    inicio = 0

    for i in range(1, len(datos) + 1):

        if i == len(datos):
            cambio = True
        else:
            cambio = (
                datos.loc[i, "tipo_vela"]
                != datos.loc[inicio, "tipo_vela"]
            )

        if cambio:

            tipo = datos.loc[inicio, "tipo_vela"]

            if tipo in ["Alcista", "Bajista"]:

                final = i - 1

                precio_inicio = datos.loc[
                    inicio,
                    "cierre"
                ]

                precio_final = datos.loc[
                    final,
                    "cierre"
                ]

                cambio_usd = (
                    precio_final - precio_inicio
                )

                cambio_pct = (
                    precio_final /
                    precio_inicio - 1
                ) * 100

                rachas.append({
                    "tipo": tipo,
                    "inicio": datos.loc[
                        inicio,
                        "fecha_utc"
                    ],
                    "fin": datos.loc[
                        final,
                        "fecha_utc"
                    ],
                    "horas": final - inicio + 1,
                    "cierre_inicial": precio_inicio,
                    "cierre_final": precio_final,
                    "cambio_usd": cambio_usd,
                    "cambio_pct": cambio_pct
                })

            inicio = i

    resultado = pd.DataFrame(rachas)

    if resultado.empty:
        return resultado

    alcista = resultado[
        resultado["tipo"] == "Alcista"
    ]

    bajista = resultado[
        resultado["tipo"] == "Bajista"
    ]

    if not alcista.empty:
        mayor_alcista = alcista.loc[
            alcista["horas"].idxmax()
        ]

        print(
            "Mayor racha alcista:",
            mayor_alcista["horas"],
            "horas"
        )

    if not bajista.empty:
        mayor_bajista = bajista.loc[
            bajista["horas"].idxmax()
        ]

        print(
            "Mayor racha bajista:",
            mayor_bajista["horas"],
            "horas"
        )

    return resultado


# ============================================================
# ACTIVIDAD 23
# DISTANCIA AL MÁXIMO DE 24 HORAS
# ============================================================

def actividad_23(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 23 - DISTANCIA AL MÁXIMO DE 24 HORAS")
    print("=" * 70)

    datos = df.copy()

    datos["maximo_24h"] = (
        datos["cierre"]
        .rolling(24, min_periods=1)
        .max()
    )

    datos["distancia_24h_pct"] = (
        datos["cierre"] /
        datos["maximo_24h"] - 1
    ) * 100

    top = datos.nsmallest(
        10,
        "distancia_24h_pct"
    ).copy()

    print(
        top[
            [
                "fecha_utc",
                "cierre",
                "maximo_24h",
                "distancia_24h_pct"
            ]
        ].to_string(index=False)
    )

    plt.figure(figsize=(13, 6))

    plt.plot(
        datos["fecha_utc"],
        datos["distancia_24h_pct"]
    )

    plt.axhline(
        0,
        linestyle="--"
    )

    plt.title(
        "Distancia del cierre respecto al máximo móvil de 24 horas"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Distancia respecto al máximo (%)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)

    guardar_grafica("23_distancia_24h.png")

    return top


# ============================================================
# ACTIVIDAD 24
# CINCO MAYORES CAÍDAS Y COMPORTAMIENTO POSTERIOR
# ============================================================

def actividad_24(df, df28):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 24 - CAÍDAS Y COMPORTAMIENTO 1/6/24 HORAS DESPUÉS")
    print("=" * 70)

    cinco = df.nsmallest(
        5,
        "cambio_pct"
    ).copy()

    datos28 = (
        df28.set_index("fecha_utc")
        .sort_index()
    )

    resultados = []

    for _, fila in cinco.iterrows():

        fecha = fila["fecha_utc"]
        cierre = fila["cierre"]

        valores = {
            "fecha_caida": fecha,
            "caida_pct": fila["cambio_pct"],
            "cierre_caida": cierre
        }

        for horas in [1, 6, 24]:

            objetivo = fecha + timedelta(hours=horas)

            if objetivo in datos28.index:

                cierre_futuro = datos28.loc[
                    objetivo,
                    "cierre"
                ]

                valores[
                    f"cierre_{horas}h"
                ] = cierre_futuro

                valores[
                    f"cambio_{horas}h_pct"
                ] = (
                    cierre_futuro / cierre - 1
                ) * 100

            else:

                valores[
                    f"cierre_{horas}h"
                ] = np.nan

                valores[
                    f"cambio_{horas}h_pct"
                ] = np.nan

        resultados.append(valores)

    resultado = pd.DataFrame(resultados)

    print(resultado.to_string(index=False))

    return resultado


# ============================================================
# ACTIVIDAD 25
# HISTOGRAMA DE CAMBIOS
# ============================================================

def actividad_25(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 25 - HISTOGRAMA DE CAMBIOS HORARIOS")
    print("=" * 70)

    cambios = df["cambio_pct"].dropna()

    mediana = cambios.median()

    percentil_extremo = cambios.abs().quantile(
        0.90
    )

    extremos = (
        cambios.abs() >= percentil_extremo
    )

    cantidad_extremos = extremos.sum()

    proporcion = (
        cantidad_extremos /
        len(cambios)
    ) * 100

    print(
        f"Mediana: {mediana:.6f}%"
    )

    print(
        f"Criterio extremo: "
        f"|cambio| >= {percentil_extremo:.6f}%"
    )

    print(
        f"Frecuencia extrema: "
        f"{cantidad_extremos} "
        f"({proporcion:.2f}%)"
    )

    plt.figure(figsize=(11, 6))

    plt.hist(
        cambios,
        bins=20
    )

    plt.axvline(
        mediana,
        linestyle="--",
        label="Mediana"
    )

    plt.title(
        "Distribución de variaciones horarias de ETHUSD"
    )

    plt.xlabel("Cambio horario (%)")
    plt.ylabel("Frecuencia")
    plt.grid(axis="y", alpha=0.3)
    plt.legend()

    guardar_grafica("25_histograma_cambios.png")

    resumen = pd.DataFrame([{
        "mediana_pct": mediana,
        "criterio_extremo_pct": percentil_extremo,
        "cantidad_extremos": cantidad_extremos,
        "proporcion_extremos_pct": proporcion
    }])

    return resumen


# ============================================================
# ACTIVIDAD 26
# SCATTER CAMBIO VS TICK VOLUME
# ============================================================

def actividad_26(df):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 26 - MOVIMIENTO VS TICK VOLUME")
    print("=" * 70)

    datos = df.dropna(
        subset=[
            "movimiento_abs_pct",
            "volumen_ticks"
        ]
    ).copy()

    correlacion = datos[
        "movimiento_abs_pct"
    ].corr(
        datos["volumen_ticks"]
    )

    print(
        f"Correlación de Pearson: "
        f"{correlacion:.6f}"
    )

    plt.figure(figsize=(10, 7))

    plt.scatter(
        datos["movimiento_abs_pct"],
        datos["volumen_ticks"],
        alpha=0.7
    )

    plt.title(
        "Movimiento absoluto horario vs tick volume"
    )

    plt.xlabel(
        "Movimiento absoluto horario (%)"
    )

    plt.ylabel(
        "Tick volume"
    )

    plt.grid(True, alpha=0.3)

    guardar_grafica("26_scatter_movimiento_ticks.png")

    resumen = pd.DataFrame([{
        "correlacion_pearson": correlacion,
        "interpretacion": (
            "Asociación estadística descriptiva; "
            "no implica causalidad."
        )
    }])

    return resumen


# ============================================================
# ACTIVIDAD 27
# OBSERVACIONES BID / ASK EN SESIÓN
# ============================================================

def actividad_27():
    print("\n" + "=" * 70)
    print("ACTIVIDAD 27 - OBSERVACIONES BID / ASK")
    print("=" * 70)

    observaciones = []

    cantidad = 5
    intervalo = 2

    print(
        f"Se tomarán {cantidad} observaciones "
        f"cada {intervalo} segundos."
    )

    for i in range(cantidad):

        tick = mt5.symbol_info_tick(SIMBOLO)

        if tick is not None:

            fecha = datetime.fromtimestamp(
                tick.time,
                tz=timezone.utc
            )

            bid = float(tick.bid)
            ask = float(tick.ask)

            observaciones.append({
                "fecha_utc": fecha,
                "bid": bid,
                "ask": ask,
                "spread": ask - bid
            })

            print(
                i + 1,
                fecha_texto(fecha),
                f"BID={bid:.2f}",
                f"ASK={ask:.2f}",
                f"SPREAD={ask-bid:.2f}"
            )

        if i < cantidad - 1:
            time.sleep(intervalo)

    datos = pd.DataFrame(observaciones)

    if datos.empty:
        return datos

    plt.figure(figsize=(13, 6))

    plt.plot(
        datos["fecha_utc"],
        datos["bid"],
        marker="o",
        label="Bid"
    )

    plt.plot(
        datos["fecha_utc"],
        datos["ask"],
        marker="o",
        label="Ask"
    )

    plt.title(
        "Observaciones de Bid y Ask durante la sesión"
    )

    plt.xlabel("Fecha y hora UTC")
    plt.ylabel("Precio (USD)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    guardar_grafica("27_bid_ask_sesion.png")

    return datos


# ============================================================
# ACTIVIDAD 28
# CUATRO SEMANAS
# ============================================================

def actividad_28():
    print("\n" + "=" * 70)
    print("ACTIVIDAD 28 - RESUMEN DE CUATRO SEMANAS")
    print("=" * 70)

    hasta = ahora_utc()
    desde = hasta - timedelta(days=28)

    df28 = obtener_velas(desde, hasta)

    if df28.empty:
        print("No se encontraron datos para cuatro semanas.")
        return df28, pd.DataFrame()

    datos = df28.copy()

    iso = datos["fecha_utc"].dt.isocalendar()

    datos["semana"] = (
        iso["year"].astype(str)
        + "-W"
        + iso["week"].astype(str).str.zfill(2)
    )

    semanal = (
        datos.groupby("semana")
        .agg(
            apertura=("apertura", "first"),
            maximo=("maximo", "max"),
            minimo=("minimo", "min"),
            cierre=("cierre", "last"),
            tick_volume=("volumen_ticks", "sum"),
            variacion_cierres_pct=(
                "cambio_pct",
                "std"
            )
        )
        .reset_index()
    )

    semanal["rango_usd"] = (
        semanal["maximo"] -
        semanal["minimo"]
    )

    semanal["cambio_semanal_pct"] = (
        semanal["cierre"].pct_change()
        * 100
    )

    print(
        semanal.to_string(index=False)
    )

    plt.figure(figsize=(12, 6))

    plt.plot(
        semanal["semana"],
        semanal["cierre"],
        marker="o"
    )

    plt.title(
        "ETHUSD - Cierre semanal durante cuatro semanas"
    )

    plt.xlabel("Semana ISO")
    plt.ylabel("Cierre (USD)")
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=30)

    guardar_grafica("28_resumen_4_semanas.png")

    return df28, semanal


# ============================================================
# ACTIVIDAD 29
# NUEVA CONSULTA Y COMPARACIÓN
# ============================================================

def actividad_29(df_nuevo):
    print("\n" + "=" * 70)
    print("ACTIVIDAD 29 - ACTUALIZACIÓN DEL ANÁLISIS")
    print("=" * 70)

    generacion_actual = ahora_utc()

    if EXCEL.exists():

        try:
            anterior = pd.read_excel(
                EXCEL,
                sheet_name="Velas_ETH"
            )

            if "fecha_utc" in anterior.columns:

                anterior["fecha_utc"] = pd.to_datetime(
                    anterior["fecha_utc"],
                    utc=True
                )

            fechas_anteriores = set(
                anterior["fecha_utc"].dropna()
            )

        except Exception:
            anterior = pd.DataFrame()
            fechas_anteriores = set()

    else:

        anterior = pd.DataFrame()
        fechas_anteriores = set()

    fechas_nuevas = set(
        df_nuevo["fecha_utc"]
    )

    nuevas = sorted(
        fechas_nuevas - fechas_anteriores
    )

    compartidas = sorted(
        fechas_nuevas & fechas_anteriores
    )

    fecha_anterior_max = (
        anterior["fecha_utc"].max()
        if not anterior.empty and
        "fecha_utc" in anterior.columns
        else pd.NaT
    )

    fecha_actual_max = (
        df_nuevo["fecha_utc"].max()
    )

    print(
        "Generación actual:",
        fecha_texto(generacion_actual)
    )

    print(
        "Última fecha anterior:",
        fecha_texto(fecha_anterior_max)
        if not pd.isna(fecha_anterior_max)
        else "No disponible"
    )

    print(
        "Última fecha actual:",
        fecha_texto(fecha_actual_max)
    )

    print(
        "Registros nuevos:",
        len(nuevas)
    )

    print(
        "Registros coincidentes:",
        len(compartidas)
    )

    comparacion = pd.DataFrame([{
        "fecha_generacion_actual": generacion_actual,
        "fecha_generacion_anterior": (
            ""
            if pd.isna(fecha_anterior_max)
            else fecha_anterior_max
        ),
        "ultima_fecha_actual": fecha_actual_max,
        "registros_consulta_actual": len(df_nuevo),
        "registros_nuevos": len(nuevas),
        "registros_compartidos": len(compartidas)
    }])

    return comparacion, nuevas


# ============================================================
# ACTIVIDAD 30
# CONSOLIDACIÓN FINAL
# ============================================================

def actividad_30(
    df,
    df100,
    diario,
    mayores_rangos,
    calidad,
    metadatos,
    alcistas_bajistas,
    movimiento_hora,
    movimiento_dia,
    alta_variacion,
    tick_volume,
    cambio_acumulado,
    rachas,
    distancia_24h,
    caidas,
    histograma,
    scatter,
    spread_sesion,
    resumen_4_semanas,
    actualizacion
):

    print("\n" + "=" * 70)
    print("ACTIVIDAD 30 - CONSOLIDACIÓN FINAL")
    print("=" * 70)

    resumen_actividades = pd.DataFrame([
        [1, "Identificación del instrumento", "ETHUSD identificado correctamente."],
        [2, "Bid / Ask / Spread", "Cotización actual obtenida desde MT5."],
        [3, "Últimas 100 velas", f"{len(df100)} registros analizados."],
        [4, "Periodo de siete días", f"{len(df)} registros horarios."],
        [5, "Calidad", "Se revisaron faltantes, duplicados e intervalos."],
        [6, "Precio máximo/mínimo", "Se identificaron extremos del periodo."],
        [7, "Mayores rangos", "Se obtuvieron las 10 velas de mayor rango."],
        [8, "Mayores subidas", "Se obtuvieron las 10 mayores subidas."],
        [9, "Mayores bajadas", "Se obtuvieron las 10 mayores bajadas."],
        [10, "Tipo de vela", "Se clasificaron velas alcistas y bajistas."],
        [11, "Resumen diario", "Se construyó OHLC diario."],
        [12, "Comparación diaria", "Se identificaron días extremos."],
        [13, "Movimiento por hora", "Se calculó promedio por hora UTC."],
        [14, "Movimiento semanal", "Se compararon días de la semana."],
        [15, "Media móvil", "Se calculó media móvil de 20 horas."],
        [16, "Alta variación", "Se utilizó percentil 90 como criterio."],
        [17, "Tick volume", "Se identificaron las 10 mayores observaciones."],
        [18, "Horario vs diario", "Se compararon ambas granularidades."],
        [19, "Control del procesamiento", "Consulta procesada correctamente."],
        [20, "Excel", "Datos y resultados almacenados en Excel."],
        [21, "Cambio acumulado", "Se calculó desde el primer cierre."],
        [22, "Rachas", "Se analizaron rachas alcistas y bajistas."],
        [23, "Distancia 24h", "Se calculó distancia al máximo móvil."],
        [24, "Caídas posteriores", "Se revisaron cambios a 1, 6 y 24 horas."],
        [25, "Histograma", "Se analizó la distribución de cambios."],
        [26, "Tick volume vs movimiento", "Se calculó correlación descriptiva."],
        [27, "Bid / Ask sesión", "Se tomaron observaciones actuales."],
        [28, "Cuatro semanas", "Se realizó resumen semanal."],
        [29, "Actualización", "Se compararon registros anteriores y nuevos."],
        [30, "Consolidación", "Se verificó el reporte final."]
    ], columns=[
        "actividad",
        "nombre",
        "resultado"
    ])

    interpretaciones = pd.DataFrame([
        [
            "ETHUSD",
            "Ethereum cotizado frente al dólar estadounidense."
        ],
        [
            "Variación",
            "Las mayores variaciones permiten identificar periodos de mayor movimiento."
        ],
        [
            "Tick volume",
            "El tick volume representa cambios de cotización del proveedor."
        ],
        [
            "Correlación",
            "Una correlación estadística no demuestra causalidad."
        ],
        [
            "Limitación",
            "Los resultados corresponden al periodo consultado y al proveedor MT5."
        ],
        [
            "Uso",
            "El análisis es descriptivo y no constituye una recomendación de compra o venta."
        ]
    ], columns=[
        "tema",
        "interpretacion"
    ])

    with pd.ExcelWriter(
        EXCEL,
        engine="openpyxl"
    ) as writer:

        hojas = {
            "Velas_ETH": df,
            "Ultimas_100": df100,
            "Resumen_diario": diario,
            "Mayores_movimientos": mayores_rangos,
            "Calidad": calidad,
            "Metadatos": metadatos,
            "Velas_alcistas": alcistas_bajistas,
            "Movimiento_hora": movimiento_hora,
            "Movimiento_dia": movimiento_dia,
            "Alta_variacion": alta_variacion,
            "Tick_volume": tick_volume,
            "Cambio_acumulado": cambio_acumulado,
            "Rachas": rachas,
            "Distancia_24h": distancia_24h,
            "Caidas_1_6_24h": caidas,
            "Histograma": histograma,
            "Scatter_ticks": scatter,
            "Spread_sesion": spread_sesion,
            "Resumen_4_semanas": resumen_4_semanas,
            "Actualizacion": actualizacion,
            "Resumen_30_actividades": resumen_actividades,
            "Interpretaciones": interpretaciones
        }

        for nombre, datos in hojas.items():

            if isinstance(datos, pd.DataFrame):
                datos = quitar_zona(datos)

                datos.to_excel(
                    writer,
                    sheet_name=nombre[:31],
                    index=False
                )

    print("\nExcel consolidado:")
    print(EXCEL)

    # --------------------------------------------------------
    # VERIFICACIÓN
    # --------------------------------------------------------

    libro = pd.ExcelFile(EXCEL)

    print("\nHojas finales:")
    for hoja in libro.sheet_names:
        datos = pd.read_excel(
            EXCEL,
            sheet_name=hoja
        )

        print(
            f"{hoja}: {len(datos)} registros"
        )

    print(
        "\nCantidad de hojas:",
        len(libro.sheet_names)
    )

    graficas = list(
        GRAFICAS.glob("*.png")
    )

    print(
        "Cantidad de gráficas:",
        len(graficas)
    )

    return resumen_actividades


# ============================================================
# INFORME VISUAL
# ============================================================

def generar_informe(
    df,
    diario,
    mayor_movimiento,
    mayor_subida,
    mayor_bajada,
    resumen_4_semanas
):

    inicio = fecha_texto(
        df["fecha_utc"].min()
    )

    fin = fecha_texto(
        df["fecha_utc"].max()
    )

    maximo = df.loc[
        df["cierre"].idxmax()
    ]

    minimo = df.loc[
        df["cierre"].idxmin()
    ]

    cambios = df["cambio_pct"].dropna()

    mediana = cambios.median()

    informe = f"""# Informe visual - Análisis de Ethereum

## 1. Instrumento

**Instrumento:** {SIMBOLO}

**Descripción:** Ethereum (USD)

**Periodo analizado:** {inicio} a {fin}

Todos los horarios del análisis están expresados en UTC.

---

## 2. Resumen del periodo

Durante el periodo analizado se obtuvieron **{len(df)} velas horarias**.

El precio máximo de cierre fue de **{maximo['cierre']:.2f} USD**, registrado el **{fecha_texto(maximo['fecha_utc'])}**.

El precio mínimo de cierre fue de **{minimo['cierre']:.2f} USD**, registrado el **{fecha_texto(minimo['fecha_utc'])}**.

La mediana de las variaciones horarias fue de **{mediana:.6f}%**.

---

## 3. Mayores movimientos

### Mayor rango horario

La vela con mayor rango presentó aproximadamente:

**{mayor_movimiento['rango_usd']:.2f} USD**

Fecha:

**{fecha_texto(mayor_movimiento['fecha_utc'])}**

### Mayor subida horaria

La mayor subida fue:

**{mayor_subida['cambio_pct']:.6f}%**

Fecha:

**{fecha_texto(mayor_subida['fecha_utc'])}**

### Mayor bajada horaria

La mayor bajada fue:

**{mayor_bajada['cambio_pct']:.6f}%**

Fecha:

**{fecha_texto(mayor_bajada['fecha_utc'])}**

---

## 4. Interpretación

El comportamiento de Ethereum durante el periodo presentó variaciones tanto positivas como negativas.

Los mayores rangos permiten identificar las horas donde existió mayor diferencia entre el máximo y el mínimo de la vela.

Las subidas y bajadas más importantes se analizaron individualmente para identificar los momentos de mayor movimiento.

---

## 5. Tick volume

El tick volume fue utilizado como indicador de actividad de cotizaciones dentro de MetaTrader 5.

Este valor **no debe interpretarse como el volumen total negociado mundialmente de Ethereum**, ya que depende de la actividad registrada por el proveedor de datos.

---

## 6. Movimiento y tick volume

Se comparó el movimiento porcentual absoluto de las velas con el tick volume.

La relación obtenida es únicamente descriptiva. Una correlación no demuestra que una variable sea causa de la otra.

---

## 7. Comportamiento posterior a las caídas

Las cinco mayores caídas horarias fueron comparadas con el precio registrado 1, 6 y 24 horas después.

Este análisis permite observar si el precio presentó recuperación, continuidad de la caída o comportamiento mixto.

No se utiliza para realizar predicciones.

---

## 8. Cuatro semanas

También se realizó una consulta ampliada de aproximadamente cuatro semanas para comparar:

- Cambio semanal.
- Rango semanal.
- Variación de los cierres.
- Tick volume.

---

## 9. Limitaciones

Los resultados dependen del periodo consultado, del proveedor de datos utilizado por MetaTrader 5 y de la disponibilidad de registros.

El análisis es histórico y descriptivo.

No constituye una recomendación financiera ni un sistema de compra o venta.

---

## 10. Conclusión

El proyecto permitió consultar y analizar Ethereum mediante MetaTrader 5 y organizar los datos utilizando Pandas.

Se calcularon indicadores horarios y diarios, variaciones porcentuales, rangos, medias móviles, rachas, distribución de movimientos, tick volume y comparación entre diferentes periodos.

Las gráficas permiten visualizar los principales movimientos del precio y las hojas de Excel conservan los resultados para su posterior revisión.

**Símbolo analizado:** {SIMBOLO}

**Periodo:** {inicio} a {fin}

**Fecha de generación:** {fecha_texto(ahora_utc())}
"""

    with open(
        INFORME,
        "w",
        encoding="utf-8"
    ) as archivo:

        archivo.write(informe)

    print(
        "\nInforme visual generado:",
        INFORME
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
# ============================================================
# MENÚ DE CELERY
# ============================================================

def menu_celery():

    while True:

        print("\n")
        print("=" * 70)
        print("                 CELERY - TAREAS EN SEGUNDO PLANO")
        print("=" * 70)

        if not CELERY_DISPONIBLE:

            print("\n[ERROR] Celery no está disponible.")

            print(
                "Detalle:",
                CELERY_ERROR
            )

            print("\nVerifica que existan:")

            print("  - tasks.py")
            print("  - celery_app.py")
            print("  - Redis funcionando")
            print("  - Worker de Celery ejecutándose")

            input(
                "\nPresiona ENTER para volver..."
            )

            return

        print("\nCelery está disponible correctamente.")

        print("\n[1] Consultar y procesar velas ETHUSD")
        print("[2] Generar y verificar gráficas")
        print("[3] Generar y verificar Excel")
        print("[4] Probar período sin datos")
        print("[5] Volver")

        opcion = input(
            "\nSeleccione una opción: "
        ).strip()

        if opcion == "5":
            print("\nVolviendo al programa principal...")
            return

        tareas = {
            "1": consultar_velas_eth,
            "2": generar_graficas_eth,
            "3": generar_excel_eth,
            "4": consultar_periodo_sin_datos
        }

        if opcion not in tareas:

            print(
                "\n[ERROR] Opción no válida."
            )

            continue

        try:

            print("\n")
            print("-" * 70)
            print("ENVIANDO TAREA A CELERY")
            print("-" * 70)

            tarea = tareas[opcion].delay()

            print(
                "ID de tarea:",
                tarea.id
            )

            print(
                "Estado inicial:",
                tarea.status
            )

            print(
                "\nEsperando resultado del worker..."
            )

            resultado = tarea.get(
                timeout=300
            )

            print("\n")
            print("-" * 70)
            print("RESULTADO DE CELERY")
            print("-" * 70)

            if isinstance(resultado, dict):

                for clave, valor in resultado.items():

                    print(
                        f"{clave}: {valor}"
                    )

            else:

                print(resultado)

            print("-" * 70)

            print(
                "\nTarea finalizada correctamente."
            )

        except Exception as error:

            print("\n")
            print("-" * 70)
            print("ERROR EJECUTANDO TAREA CELERY")
            print("-" * 70)

            print(
                type(error).__name__,
                ":",
                error
            )

            print("\nPosibles causas:")

            print(
                "1. Redis no está iniciado."
            )

            print(
                "2. El worker de Celery no está ejecutándose."
            )

            print(
                "3. MetaTrader 5 no está abierto o conectado."
            )

            print(
                "4. Existe un problema en tasks.py."
            )

        input(
            "\nPresiona ENTER para continuar..."
        )
def main():

    print("\n")
    print("=" * 70)
    print("PROYECTO DE MINERÍA DE DATOS")
    print("ANÁLISIS DE ETHEREUM CON METATRADER 5")
    print("=" * 70)

    print(
        "\nPeriodo de análisis:",
        DIAS_ANALISIS,
        "días"
    )

    print(
        "Símbolo:",
        SIMBOLO
    )
def main():

    if not comprobar_mt5():
        return

    try:

        # ----------------------------------------------------
        # INFORMACIÓN DEL SÍMBOLO
        # ----------------------------------------------------

        info = mt5.symbol_info(SIMBOLO)

        # ----------------------------------------------------
        # ACTIVIDADES 1 Y 2
        # ----------------------------------------------------

        datos_1 = actividad_1(info)

        datos_2 = actividad_2(info)

        # ----------------------------------------------------
        # ACTIVIDAD 3
        # ----------------------------------------------------

        df100 = actividad_3()

        # ----------------------------------------------------
        # ACTIVIDAD 4
        # ----------------------------------------------------

        df = actividad_4()

        if df.empty:
            print(
                "\nNo hay datos suficientes para continuar."
            )
            return

        # ----------------------------------------------------
        # ACTIVIDAD 5
        # ----------------------------------------------------

        calidad = actividad_5(df)

        # ----------------------------------------------------
        # ACTIVIDAD 6
        # ----------------------------------------------------

        extremos = actividad_6(df)

        # ----------------------------------------------------
        # ACTIVIDADES 7-10
        # ----------------------------------------------------

        mayores_rangos = actividad_7(df)

        mayores_subidas = actividad_8(df)

        mayores_bajadas = actividad_9(df)

        tipo_velas = actividad_10(df)

        # ----------------------------------------------------
        # ACTIVIDADES 11-18
        # ----------------------------------------------------

        diario = actividad_11(df)

        comparacion_diaria = actividad_12(diario)

        movimiento_hora = actividad_13(df)

        movimiento_dia = actividad_14(df)

        media_movil, cruces = actividad_15(df)

        alta_variacion, percentil = actividad_16(df)

        tick_volume = actividad_17(df)

        comparacion_horaria = actividad_18(
            df,
            diario
        )

        # ----------------------------------------------------
        # ACTIVIDAD 19
        # ----------------------------------------------------

        control_proceso = actividad_19(df)

        # ----------------------------------------------------
        # METADATOS
        # ----------------------------------------------------

        generacion = ahora_utc()

        metadatos = pd.DataFrame([
            ["Símbolo", SIMBOLO],
            ["Descripción", info.description],
            ["Moneda", info.currency_profit],
            ["Timeframe", "H1"],
            ["Periodo solicitado", f"{DIAS_ANALISIS} días"],
            ["Inicio real", fecha_texto(df["fecha_utc"].min())],
            ["Fin real", fecha_texto(df["fecha_utc"].max())],
            ["Registros horarios", len(df)],
            ["Fecha de generación", fecha_texto(generacion)],
            ["Zona horaria", "UTC"],
            ["Fuente", "MetaTrader 5"],
            ["Tipo de análisis", "Histórico y descriptivo"],
            ["Operaciones", "No se realizan compras ni ventas"]
        ], columns=[
            "campo",
            "valor"
        ])

        # ----------------------------------------------------
        # ACTIVIDAD 20
        # ----------------------------------------------------

        actividad_20(
            df,
            df100,
            diario,
            mayores_rangos,
            calidad,
            metadatos,
            tipo_velas,
            movimiento_hora,
            movimiento_dia,
            alta_variacion,
            tick_volume
        )

        # ----------------------------------------------------
        # ACTIVIDAD 21
        # ----------------------------------------------------

        cambio_acumulado = actividad_21(df)

        # ----------------------------------------------------
        # ACTIVIDAD 22
        # ----------------------------------------------------

        rachas = actividad_22(df)

        # ----------------------------------------------------
        # ACTIVIDAD 23
        # ----------------------------------------------------

        distancia_24h = actividad_23(df)

        # ----------------------------------------------------
        # ACTIVIDAD 24
        # ----------------------------------------------------

        ahora = ahora_utc()

        df28_para_24 = obtener_velas(
            ahora - timedelta(days=28),
            ahora
        )

        caidas = actividad_24(
            df,
            df28_para_24
        )

        # ----------------------------------------------------
        # ACTIVIDAD 25
        # ----------------------------------------------------

        histograma = actividad_25(df)

        # ----------------------------------------------------
        # ACTIVIDAD 26
        # ----------------------------------------------------

        scatter = actividad_26(df)

        # ----------------------------------------------------
        # ACTIVIDAD 27
        # ----------------------------------------------------

        spread_sesion = actividad_27()

        # ----------------------------------------------------
        # ACTIVIDAD 28
        # ----------------------------------------------------

        df28, resumen_4_semanas = actividad_28()

        # ----------------------------------------------------
        # ACTIVIDAD 29
        # ----------------------------------------------------

        actualizacion, registros_nuevos = actividad_29(
            df
        )

        # ----------------------------------------------------
        # ACTIVIDAD 30
        # ----------------------------------------------------

        resumen_final = actividad_30(
            df=df,
            df100=df100,
            diario=diario,
            mayores_rangos=mayores_rangos,
            calidad=calidad,
            metadatos=metadatos,
            alcistas_bajistas=tipo_velas,
            movimiento_hora=movimiento_hora,
            movimiento_dia=movimiento_dia,
            alta_variacion=alta_variacion,
            tick_volume=tick_volume,
            cambio_acumulado=cambio_acumulado,
            rachas=rachas,
            distancia_24h=distancia_24h,
            caidas=caidas,
            histograma=histograma,
            scatter=scatter,
            spread_sesion=spread_sesion,
            resumen_4_semanas=resumen_4_semanas,
            actualizacion=actualizacion
        )

        # ----------------------------------------------------
        # INFORME VISUAL
        # ----------------------------------------------------

        mayor_movimiento = mayores_rangos.iloc[0]

        mayor_subida = mayores_subidas.iloc[0]

        mayor_bajada = mayores_bajadas.iloc[0]

        generar_informe(
            df,
            diario,
            mayor_movimiento,
            mayor_subida,
            mayor_bajada,
            resumen_4_semanas
        )

        # ----------------------------------------------------
        # RESUMEN FINAL
        # ----------------------------------------------------

        print("\n")
        print("=" * 70)
        print("PROCESO FINALIZADO CORRECTAMENTE")
        print("=" * 70)

        print(
            "\nExcel:",
            EXCEL
        )

        print(
            "Informe:",
            INFORME
        )

        print(
            "Gráficas:",
            GRAFICAS
        )

        print(
            "\nActividades completadas: 1-30"
        )

        print(
            "Celery: INTEGRADO AL PROYECTO"
        )

    except Exception as error:

        print("\n")
        print("=" * 70)
        print("ERROR DURANTE EL ANÁLISIS")
        print("=" * 70)

        print(
            "Tipo de error:",
            type(error).__name__
        )

        print(
            "Detalle:",
            error
        )

        traceback.print_exc()

    finally:

        mt5.shutdown()

        print(
            "\nMetaTrader 5 desconectado."
        )

    # --------------------------------------------------------
    # MENÚ CELERY
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("MENÚ PRINCIPAL")
    print("=" * 70)

    print(
        "[31] Ejecutar tareas con Celery"
    )

    print(
        "[0] Finalizar programa"
    )

    opcion_menu = input(
        "\nSeleccione una opción: "
    ).strip()

    if opcion_menu == "31":

        menu_celery()

    elif opcion_menu == "0":

        print(
            "\nPrograma finalizado."
        )

    else:

        print(
            "\nOpción no válida."
        )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()
   