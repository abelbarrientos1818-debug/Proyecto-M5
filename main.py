import os
import streamlit as st

st.title("Asesor de Jugadores")
st.caption("Te ayudamos a encontrar el mejor salario con DATOS")

# AÑADE ESTA LÍNEA AQUÍ
st.write("¡Bienvenido! Usa la caja de chat de abajo para hacer tus preguntas.")

prompt = st.chat_input("En qué te puedo ayudar?")
if prompt:
    st.write(f"El usuario ha enviado el siguiente prompt: '{prompt}'")