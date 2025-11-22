import os
import streamlit as st
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
from prompts import stronger_prompt 
import json
from tools import tools_definition, analyze_player_tool # Importar desde tu nuevo archivo

# ----------------------------------------------------
# 0. CONFIGURACIÓN E INICIALIZACIÓN DE API
# ----------------------------------------------------

load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    client_openai = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Error al inicializar el cliente de OpenAI. Asegura que OPENAI_API_KEY está en tu .env: {e}")
    client_openai = None

MODEL_CHAT = "gpt-4o-mini" 
MODEL_TRANSCRIPT = "whisper-1" 
MODEL_TTS = "tts-1" 
VOICE_TTS = "fable" 

# ----------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA (Brainiac)
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
    st.session_state["messages"] = [{"role": "assistant", "content": "Soy **Brainiac**. ¿Qué datos quieres condensar sobre tu valor salarial?"}]

# ----------------------------------------------------
# 3. BARRA LATERAL: ENTRADA DE AUDIO DIRECTA (¡Grabación en vivo!)
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
        st.session_state["messages"] = [{"role": "assistant", "content": "Intelecto reiniciado. ¿Qué datos quieres condensar sobre tu valor salarial?"}]
        st.rerun() # <<< CORRECCIÓN APLICADA AQUÍ
    st.info(f"Modelo de Chat: {MODEL_CHAT}")

# ----------------------------------------------------
# 4. CONTENEDOR PRINCIPAL DEL CHAT Y LÓGICA DE PROCESAMIENTO
# ----------------------------------------------------

for msg in st.session_state.messages:
    message_block = st.chat_message(msg["role"])
    message_block.write(msg["content"])
    audio_payload = msg.get("audio")
    if audio_payload:
         message_block.audio(audio_payload, format="audio/mp3", autoplay=False) 

user_prompt = None
user_display_content = None

# A. Lógica de entrada de texto
if text_prompt := st.chat_input(placeholder="Escribe aquí para condensar datos..."):
    user_prompt = text_prompt
    user_display_content = text_prompt

# B. Lógica de entrada de audio
elif send_audio and client_openai:
    
    if audio_value is not None:
        raw_audio = audio_value.getvalue()
        audio_file = BytesIO(raw_audio)
        audio_file.name = "voz_usuario.wav"
        source = "Audio grabado"
        
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
                    st.info("La transcripción no contiene texto interpretable. Intenta nuevamente.")
            except Exception as e:
                st.error(f"Error al transcribir el audio: {e}")
                user_prompt = None
    else:
        st.warning("Graba un mensaje de voz antes de presionar 'Enviar Audio'.")

# ----------------------------------------------------
# C. LÓGICA PRINCIPAL (TEXTO + HERRAMIENTAS + AUDIO)
# ----------------------------------------------------

if user_prompt and client_openai:
    
    # 1. Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.chat_message("user").write(user_display_content or user_prompt)
    
    # 2. Preparar contexto para la IA
    # Usamos el prompt fuerte como sistema y filtramos el historial para no duplicar system messages
    conversation = [{"role": "system", "content": stronger_prompt}] 
    conversation.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] != "system"])

    full_response = ""
    audio_bytes = None

    with st.chat_message("assistant"):
        with st.spinner("Brainiac está analizando los datos..."):
            try:
                # -------------------------------------------------
                # PASO A: Primera llamada (Decisión: ¿Texto o Tool?)
                # -------------------------------------------------
                first_response = client_openai.chat.completions.create(
                    model=MODEL_CHAT,
                    messages=conversation,
                    tools=tools_definition,
                    tool_choice="auto"
                )
                
                msg = first_response.choices[0].message

                # -------------------------------------------------
                # PASO B: Si la IA decide usar la HERRAMIENTA
                # -------------------------------------------------
                if msg.tool_calls:
                    conversation.append(msg) # Añadimos la intención al historial temporal
                    
                    for tool_call in msg.tool_calls:
                        if tool_call.function.name == "analyze_player_tool":
                            args = json.loads(tool_call.function.arguments)
                            
                            # Feedback visual elegante (Toast)
                            st.toast(f"🔍 Consultando base de datos para: {args['player_name']}...", icon="⚽")
                            
                            # Ejecutar la función Python real (tools.py)
                            tool_result = analyze_player_tool(args['player_name'], client_openai)
                            
                            # Añadir el resultado (JSON) al historial para que la IA lo lea
                            conversation.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result)
                            })
                    
                    # Segunda llamada: La IA genera la respuesta final con los datos
                    stream = client_openai.chat.completions.create(
                        model=MODEL_CHAT,
                        messages=conversation,
                        stream=True
                    )
                    full_response = st.write_stream(stream)
                    
                # -------------------------------------------------
                # PASO C: Si es charla normal (sin herramientas)
                # -------------------------------------------------
                else:
                    # Hacemos streaming directo
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
    # PASO D: GENERACIÓN DE AUDIO (TTS) - ¡AQUÍ ESTÁ!
    # -------------------------------------------------
    if full_response and not full_response.startswith("⚠️"):
        with st.spinner("Brainiac está sintetizando la voz..."):
            try:
                speech = client_openai.audio.speech.create(
                    model=MODEL_TTS, 
                    voice=VOICE_TTS, 
                    input=full_response
                )
                audio_bytes = speech.content
                
                # Reproducir automáticamente
                st.audio(audio_bytes, format="audio/mp3", autoplay=True, loop=False)

            except Exception as exc:
                st.warning(f"No se pudo generar el audio: {exc}")

    # -------------------------------------------------
    # PASO E: GUARDAR EN HISTORIAL (Texto + Audio)
    # -------------------------------------------------
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response, 
        "audio": audio_bytes # ¡Guardamos el audio para que no se pierda!
    })

    # Forzar rerun si vino del botón de audio para limpiar la UI
    if send_audio:
        st.rerun()