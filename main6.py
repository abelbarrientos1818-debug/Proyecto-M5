import os
import json
import streamlit as st
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

# ----------------------------------------------------
# IMPORTACIONES LOCALES 
# ----------------------------------------------------
# Importamos el prompt maestro
from prompts import final_system_prompt 
# Importamos la definición de herramientas y las funciones lógicas de tools
from tools import tools_definition, analyze_player_tool, lookup_database_tool

# ----------------------------------------------------
# 0. CONFIGURACIÓN E INICIALIZACIÓN DE API
# ----------------------------------------------------

load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    client_openai = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Error")
    client_openai = None

MODEL_CHAT = "gpt-5-mini" 
MODEL_TRANSCRIPT = "whisper-1" 
MODEL_TTS = "tts-1" 
VOICE_TTS = "fable" 

# ----------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA 
# ----------------------------------------------------

st.set_page_config(
    page_title="Kal-El Analytics - Brainiac Chat",
    page_icon="🧠", 
    layout="wide"
)

st.markdown(
    """
    <h1 style='color: #00FF00;'>
        Brainiac: Asistente Analítico 🧠
    </h1>
    <h3 style='color: #FFFFFF;'>
        Analizamos cada universo de datos para condensar tu valor real.
    </h3>
    <hr style="border: 2px solid #5D3FD3;">
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# 2. INICIALIZACIÓN DEL CHAT
# ----------------------------------------------------

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant", 
            "content": (
                "👋 **¡Hola! Soy Brainiac, tu agente experto en valoración salarial.** 🧠⚽\n\n"
                "Estoy aquí para ayudarte a negociar tu próximo contrato con datos reales. "
                "¿Cómo te gustaría comenzar hoy?\n\n"
                "🔹 **Simular un Contrato:** Dime tu nombre, año de nacimiento, equipo te gustaría ir o renovar contrato y país de la liga. \n\n"
                "🔹 **Consultar Datos:** Pregúntame sobre la masa salarial de un club, los impuestos o costo de vida en un país.\n\n"
                "🔹 **Análisis de Rendimiento:** Pídeme revisar tus métricas actuales.\n\n"
                "*¡Escribe o graba tu mensaje para empezar!* 🎙️"
            )
        }
    ]

# ----------------------------------------------------
# 3. BARRA LATERAL: ENTRADA DE AUDIO
# ----------------------------------------------------
audio_value = None
send_audio = False 

with st.sidebar:
    st.title("Kal-El Analytics")
    st.caption("Consolidando el conocimiento de tu valor.")
    st.markdown("---")
    st.header("⚙️ Entrada de Voz Directa")
    
    audio_value = st.audio_input("Graba un mensaje de voz", key="audio_recorder")
    send_audio = st.button("Enviar Audio a Brainiac", key="send_audio_button", use_container_width=True)
    
    st.markdown("---")
    
    
    
    if st.button("Reiniciar Conversación", use_container_width=True):
        st.session_state["messages"] = [
            {
                "role": "assistant", 
                "content": (
                    "👋 **¡Hola! Soy Brainiac, tu agente experto en valoración salarial.** 🧠⚽\n\n"
                    "Estoy aquí para ayudarte a negociar tu próximo contrato con datos reales. "
                    "**¿Por dónde quieres empezar?**\n\n"
                    "🎯 **Simular un Contrato:** Dime el nombre del jugador, año, equipo y país destino.\n"
                    "💰 **Consultar Finanzas:** Pregunta por la masa salarial de un club o impuestos de una liga.\n"
                    "📊 **Ver Rendimiento:** Pídeme las estadísticas clave de un jugador.\n\n"
                    "*¡Escribe o graba tu mensaje para empezar!* 🎙️"
                )
            }
        ]
        st.rerun() 
        
    st.info(f"Modelo de Chat: {MODEL_CHAT}")

# ----------------------------------------------------
# 4. CONTENEDOR PRINCIPAL Y LÓGICA
# ----------------------------------------------------

# Mostrar historial de mensajes anteriores
for msg in st.session_state.messages:
    message_block = st.chat_message(msg["role"])
    message_block.write(msg["content"])
    # Si el mensaje tiene audio mostrar el reproductor
    audio_payload = msg.get("audio")
    if audio_payload:
         message_block.audio(audio_payload, format="audio/mp3", autoplay=False) 

user_prompt = None
user_display_content = None

#Logica de entrada de texto
if text_prompt := st.chat_input(placeholder="Escribe aquí para condensar datos..."):
    user_prompt = text_prompt
    user_display_content = text_prompt

#Logica de entrada de audio 
elif send_audio and client_openai:
    if audio_value is not None:
        raw_audio = audio_value.getvalue()
        audio_file = BytesIO(raw_audio)
        audio_file.name = "voz_usuario.wav"
        
        with st.spinner("Brainiac está transcribiendo el audio..."):
            try:
                transcription = client_openai.audio.transcriptions.create(
                    model=MODEL_TRANSCRIPT,
                    file=audio_file,
                )
                user_prompt = transcription.text.strip()
                if user_prompt:
                    user_display_content = f"**(Transcripción):** {user_prompt}"
                else:
                    st.info("La transcripción no contiene texto interpretable.")
            except Exception as e:
                st.error(f"Error al transcribir el audio: {e}")
                user_prompt = None
    else:
        st.warning("Graba un mensaje de voz antes de presionar 'Enviar Audio'.")

# ----------------------------------------------------
# FUNCTION CALLING + TTS
# ----------------------------------------------------

if user_prompt and client_openai:
    
    # 1. Mostrar mensaje del usuario en el chat
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.chat_message("user").write(user_display_content or user_prompt)
    
    # 2. Preparar contexto para la IA
    # Inyectamos el prompt 
    conversation = [{"role": "system", "content": final_system_prompt}] 
    
    # Añadimos el historial 
    conversation.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] != "system"])

    full_response = ""
    audio_bytes = None

    with st.chat_message("assistant"):
        with st.spinner("Brainiac está analizando los datos..."):
            try:
                # -------------------------------------------------
                # PASO A: Primera llamada (¿Necesito herramientas?)
                # -------------------------------------------------
                first_response = client_openai.chat.completions.create(
                    model=MODEL_CHAT,
                    messages=conversation,
                    tools=tools_definition,
                    tool_choice="auto"
                )
                
                msg = first_response.choices[0].message

                # -------------------------------------------------
                # PASO B: Si Braniac decide usar HERRAMIENTAS
                # -------------------------------------------------
                if msg.tool_calls:
                    conversation.append(msg) 
                    
                    for tool_call in msg.tool_calls:
                        args = json.loads(tool_call.function.arguments)
                        tool_result = {}
                        
                        # --- CASO 1: ANÁLISIS DE JUGADOR (Predicción) ---
                        if tool_call.function.name == "analyze_player_tool":
                            p_name = args.get('player_name')
                            # 1. CAPTURAR EL AÑO (Nuevo)
                            p_year = args.get('birth_year') 
                            
                            # Actualizamos el mensaje visual
                            st.toast(f"🔍 Analizando a: {p_name} ({p_year})...", icon="⚽")
                            
                            # 2. PASAR EL AÑO A LA FUNCIÓN 
                            tool_result = analyze_player_tool(
                                player_name=p_name,
                                birth_year=p_year,  
                                client_openai=client_openai,
                                target_club=args.get('target_club'),
                                target_league=args.get('target_league')
                            )
                        
                        # --- CASO 2: CONSULTA DE DATOS  ---
                        elif tool_call.function.name == "lookup_database_tool":
                            target = args.get('name')
                            cat = args.get('category')
                            st.toast(f"📂 Consultando datos de {target}...", icon="🗃️")
                            
                            tool_result = lookup_database_tool(
                                category=cat,
                                name=target
                            )
                            
                        # Guardar el resultado de la herramienta en la conversación
                        conversation.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result)
                        })
                    
                    # -------------------------------------------------
                    # PASO C: Segunda llamada (Generar respuesta final con datos)
                    # -------------------------------------------------
                    stream = client_openai.chat.completions.create(
                        model=MODEL_CHAT,
                        messages=conversation,
                        stream=True
                    )
                    full_response = st.write_stream(stream)
                    
                # -------------------------------------------------
                # PASO D: Si es charla normal 
                # -------------------------------------------------
                else:
                    stream = client_openai.chat.completions.create(
                        model=MODEL_CHAT,
                        messages=conversation,
                        stream=True
                    )
                    full_response = st.write_stream(stream)

            except Exception as e:
                full_response = f"⚠️ Error en el procesamiento: {e}"
                st.error(full_response)

    # -------------------------------------------------
    # PASO E: Generar Audio (TTS)
    # -------------------------------------------------
    if full_response and not full_response.startswith("⚠️"):
        # Limitamos por temas de tiempo
        tts_input = full_response[:4096] 
        
        # Solo generamos audio si hay una respuesta válida
        with st.spinner("Brainiac está sintetizando la voz..."):
            try:
                speech = client_openai.audio.speech.create(
                    model=MODEL_TTS, 
                    voice=VOICE_TTS, 
                    input=tts_input
                )
                audio_bytes = speech.content
                
                # Reproducir automáticamente en la interfaz
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)

            except Exception as exc:
                st.warning(f"No se pudo generar el audio: {exc}")

    # -------------------------------------------------
    # PASO F: Guardar respuesta en historial 
    # -------------------------------------------------
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response, 
        "audio": audio_bytes # Guardamos el audio para poder reproducirlo después
    })

    
    
    if send_audio:
        st.rerun()