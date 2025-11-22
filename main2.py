import streamlit as st

# ----------------------------------------------------
# 1. CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO)
# ----------------------------------------------------
st.set_page_config(
    page_title="Kal-El Analytics - Asesor de Contratos",
    page_icon="🛡️",  # Ícono del escudo de Superman
    layout="wide"  # Usa todo el ancho de la pantalla
)

# ----------------------------------------------------
# 2. BARRA LATERAL (El Escudo Amarillo)
# ----------------------------------------------------
with st.sidebar:
    # --- BLOQUE DE ESTILO CSS PARA TEXTO AZUL SOBRE FONDO AMARILLO ---
    st.markdown(
        """
        <style>
        /* Selecciona todos los elementos de texto dentro de la barra lateral */
        .st-emotion-cache-1c5v44j div, 
        .st-emotion-cache-1c5v44j p, 
        .st-emotion-cache-1c5v44j h1, 
        .st-emotion-cache-1c5v44j h2, 
        .st-emotion-cache-1c5v44j h3,
        .st-emotion-cache-1c5v44j .stButton > button {
            color: #0047AB !important; /* Azul Profundo de Superman */
        }
        
        /* Aseguramos que los títulos, aunque se vean azules, no tengan el estilo H1 forzado */
        h1, h2, h3 { color: #0047AB !important; }
        
        /* Ajuste para que los botones simples no tengan un fondo rojo, sino que sean transparentes */
        .stButton button {
            background-color: transparent !important;
            border-color: #0047AB !important; /* Borde azul */
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # --- FIN DEL BLOQUE DE ESTILO ---
    
    # El título (Azul)
    st.markdown(
        """
        <h1 style='color: #0047AB;'>Kal-El Analytics</h1>
        """,
        unsafe_allow_html=True
    )
    
    # El eslogan (Azul)
    st.caption("Tu valor es de Acero, tu contrato debe serlo.")
    st.markdown("---")
    
    st.header("🏢 Módulos")
    # Esqueleto de Navegación sin funcionalidad
    st.button("Dashboard de Jugadores", use_container_width=True)
    st.button("Análisis de Contratos", use_container_width=True)
    st.button("Reportes Personalizados", use_container_width=True)
    
    st.markdown("---")
    st.write("Estado: Conectado (Aquí irá tu lógica de login)")

# ----------------------------------------------------
# 3. ÁREA PRINCIPAL (Sobre fondo Azul)
# ----------------------------------------------------

# Título Principal (Ahora en AMARILLO para alto contraste) y Subtítulo (Rojo Fuego)
st.markdown(
    """
    <h1 style='color: #FDEE21;'>
        Bienvenido al Asesor de Jugadores 🛡️
    </h1>
    <h3 style='color: #E30B13;'>
        La Inteligencia de Mercado que Necesitas
    </h3>
    <hr style="border: 3px solid #E30B13;">
    """,
    unsafe_allow_html=True
)
# Secciones de Métricas Clave (Estructura de tres columnas)
st.subheader("📊 Resumen de Datos Clave")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    # st.metric es excelente para visualizaciones profesionales
    st.metric(label="Jugadores en la Base", value="1,245")
    st.empty() # Placeholder: Aquí irá una tabla o gráfica en el futuro

with col2:
    st.metric(label="Salario Promedio Estimado", value="$4.2 M", delta="4.2%", delta_color="normal")
    st.empty() # Placeholder: Aquí irá un filtro o un slider en el futuro

with col3:
    st.metric(label="Tasa de Éxito en Negociación", value="89%", delta="1%", delta_color="normal")
    # El botón usará automáticamente el color rojo (#E30B13) definido en config.toml
    st.button("Iniciar Nuevo Análisis", type="primary", use_container_width=True) 

st.markdown("---")

# Sección de Interacción Principal (El Chat)
st.subheader("💬 Asistente de Negociación")

# El input del chat listo para tu lógica
chat_input = st.chat_input("Escribe tu pregunta sobre valoraciones o contratos aquí...")

# Esqueleto de lógica: Solo muestra el prompt para probar
if chat_input:
    st.success(f"🤖 Procesando: '{chat_input}'...")
    # st.empty() # Aquí irá la respuesta del modelo GPT en el futuro

# Esqueleto de la sección de visualización de datos
st.subheader("📈 Visualización de Contratos")
st.empty() # Placeholder grande

# ----------------------------------------------------
# 4. INSTRUCCIONES PARA EJECUTAR
# ----------------------------------------------------

# Nota: No necesitas estas líneas en tu main.py final, son solo instrucciones.
# print("Guarda este archivo como main.py y el otro en .streamlit/config.toml")
# print("Ejecuta con: uv run streamlit run main.py")