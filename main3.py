import streamlit as st
from math import exp
import pandas as pd

# ----------------------------------------------------
# 0. DATOS Y LÓGICA DE SIMULACIÓN (Tus cálculos)
# ----------------------------------------------------

# 🚨 DATOS DE EVALUACIÓN (Input del Jugador)
X_input_dict = {
    'Age': 24, 'SCA90': 2.0, 'GCA90': 0.0, 'COV_Factor': 0.996665,
    'Tax_Rate': 0.494606, 'Masa_Salarial_X': 62764000.0,
    # ... (el resto de tus variables de input)
    'Comp_Premier League': 1.0, 
}

# 🚨 PARÁMETROS DEL MODELO
MODEL_RMSE_EUROS = 166930.16 
Z_SCORE_95 = 1.96
LOG_SALARY_PREDICTED = 13.1615 # Simulación Log(520,000 EUR)

def calcular_banda_salarial(log_pred):
    """Simula el cálculo de tu Módulo 6."""
    salario_bruto_anual = exp(log_pred)
    
    # Ajuste socioeconómico
    tax_rate = X_input_dict['Tax_Rate']
    cov_factor = X_input_dict['COV_Factor']
    salario_neto_anual_base = salario_bruto_anual * (1 - tax_rate) * cov_factor
    
    # Cálculo de la banda
    error_banda = Z_SCORE_95 * MODEL_RMSE_EUROS
    limite_inferior = salario_neto_anual_base - error_banda
    limite_superior = salario_neto_anual_base + error_banda
    
    # Retornamos un diccionario con los resultados
    return {
        "Bruto_Predicho": salario_bruto_anual,
        "Neto_Base": salario_neto_anual_base,
        "Inferior": limite_inferior,
        "Superior": limite_superior,
        "Tasa_Imp": tax_rate,
        "RMSE": MODEL_RMSE_EUROS
    }

resultados = calcular_banda_salarial(LOG_SALARY_PREDICTED)

# ----------------------------------------------------
# 1. CONFIGURACIÓN Y TEMA (Superman Look - Mantiene tu diseño)
# ----------------------------------------------------
st.set_page_config(
    page_title="Kal-El Analytics - Asesor de Contratos",
    page_icon="🛡️",
    layout="wide"
)

# ... (Bloque de la barra lateral st.sidebar: se mantiene el código del punto anterior para el look Amarillo/Azul)
# Nota: Si usaste mi código anterior, solo debes asegurar que el bloque st.sidebar esté aquí.
with st.sidebar:
    st.markdown(
        """
        <style>
        .st-emotion-cache-1c5v44j div, .st-emotion-cache-1c5v44j p, .st-emotion-cache-1c5v44j h1, 
        .st-emotion-cache-1c5v44j h2, .st-emotion-cache-1c5v44j h3, .st-emotion-cache-1c5v44j .stButton > button {
            color: #0047AB !important; /* Texto Azul sobre Amarillo */
        }
        h1, h2, h3 { color: #0047AB !important; }
        .stButton button { background-color: transparent !important; border-color: #0047AB !important; }
        </style>
        <h1 style='color: #0047AB;'>Kal-El Analytics</h1>
        """,
        unsafe_allow_html=True
    )
    st.caption("Tu valor es de Acero, tu contrato debe serlo.")
    st.markdown("---")
    st.header("🏢 Módulos")
    st.button("Dashboard de Jugadores", use_container_width=True)
    st.button("Análisis de Contratos", use_container_width=True)
    st.button("Reportes Personalizados", use_container_width=True)
    st.markdown("---")
    st.write("Estado: Conectado")


# ----------------------------------------------------
# 3. ÁREA PRINCIPAL: RESULTADOS DE NEGOCIACIÓN
# ----------------------------------------------------

st.markdown(
    """
    <h1 style='color: #FDEE21;'>
        Análisis de Valoración Salarial 🛡️
    </h1>
    <h3 style='color: #E30B13;'>
        Jugador: [Nombre del Jugador] - Club: Premier League
    </h3>
    <hr style="border: 3px solid #E30B13;">
    """,
    unsafe_allow_html=True
)

## SECCIÓN 1: PREDICCIÓN BASE Y AJUSTES

st.subheader("1. Predicción Base y Ajustes Socioeconómicos")

col_bruto, col_impuesto, col_ajuste = st.columns(3)

with col_bruto:
    st.metric(
        label="Salario Bruto Predicho (Modelo)", 
        value=f"€{resultados['Bruto_Predicho']:,.0f}", 
        delta=f"RMSE: €{resultados['RMSE']:,.0f}",
        delta_color="off" # Para mostrar el RMSE sin la flecha verde
    )

with col_impuesto:
    st.metric(
        label="Tasa Impositiva Aplicada", 
        value=f"{resultados['Tasa_Imp'] * 100:.2f}%", 
        delta="Factor COV: 0.997"
    )

with col_ajuste:
    # Usamos el color rojo del primaryColor para resaltar el ajuste final
    st.metric(
        label="Salario Neto Base Ajustado", 
        value=f"€{resultados['Neto_Base']:,.0f}",
        delta="Base para la Negociación"
    )

st.markdown("---")

## SECCIÓN 2: BANDA SALARIAL Y NEGOCIACIÓN (El núcleo del proyecto)

st.subheader("2. 🎯 Banda Salarial Neta Recomendada (95% Confianza)")

# Usamos una columna más ancha para mostrar la banda completa
col_banda_inf, col_banda_media, col_banda_sup = st.columns([1, 2, 1])

with col_banda_inf:
    # Límite Inferior (Rojo, para indicar el mínimo aceptable)
    st.error(f"### Límite Inferior: \n\n €{resultados['Inferior']:,.0f}")

with col_banda_media:
    # El punto medio o ideal de negociación (Amarillo/Azul, usando markdown para color)
    st.markdown(
        f"""
        <div style='background-color:#FDEE21; padding: 10px; border-radius: 5px; text-align: center;'>
            <h3 style='color:#0047AB; margin: 0;'>Punto de Negociación Óptimo</h3>
            <h1 style='color:#E30B13; font-size: 2.5em; margin: 5px 0;'>€{resultados['Neto_Base']:,.0f}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.info("Esta banda se calcula con un margen de error del modelo del **$1.96 \times$ RMSE**.")


with col_banda_sup:
    # Límite Superior (Rojo, para indicar el máximo aceptable)
    st.error(f"### Límite Superior: \n\n €{resultados['Superior']:,.0f}")

st.markdown("---")

## SECCIÓN 3: CHAT Y DETALLE DE INPUTS (Para el final)
st.subheader("3. Detalle de Inputs y Asistente")

# Muestra los inputs del jugador para referencia
with st.expander("Ver todas las 30+ Variables de Input del Jugador"):
    st.json(X_input_dict) # Usa st.json para mostrar el diccionario ordenado

# st.chat_input se mantiene para la interacción futura con Clark Kent

# ... (Bloque de chat se puede omitir por ahora, o dejar como placeholder)
st.chat_input("Escribe tu pregunta sobre la banda salarial...")