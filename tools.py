import pandas as pd
import numpy as np
import xgboost as xgb
import json
import os
import unicodedata
import difflib
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

# ==========================================
# 0. UTILIDADES DE TEXTO
# ==========================================
def normalizar_texto(texto):
    """Normalización robusta para búsqueda de nombres."""
    if not isinstance(texto, str): return str(texto)
    texto = texto.replace("Ø", "O").replace("ø", "o")
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

def encontrar_coincidencia_difusa(nombre, lista_opciones, umbral=0.6):
    """Encuentra el nombre más parecido en una lista."""
    nombre_norm = normalizar_texto(nombre)
    opciones_norm = [normalizar_texto(x) for x in lista_opciones]
    
    coincidencias = difflib.get_close_matches(nombre_norm, opciones_norm, n=1, cutoff=umbral)
    
    if coincidencias:
        idx = opciones_norm.index(coincidencias[0])
        return lista_opciones[idx]
    return None

# ==========================================
# 1. CARGA DE ARTEFACTOS
# ==========================================
print("⚙️ Cargando cerebro de Braniac...")

MODEL_FILE = "braniac_model.json"
FEATURES_FILE = "model_features.json"
REFS_FILE = "braniac_references.json"
PLAYERS_FILE = "base_datos_jugadores.csv"

try:
    model = xgb.Booster()
    model.load_model(MODEL_FILE)

    with open(FEATURES_FILE, "r") as f:
        feature_columns = json.load(f)

    with open(REFS_FILE, "r") as f:
        refs = json.load(f)
        CLUB_DICT = {k.lower().strip(): v for k, v in refs["club_finance"].items()}
        SOCIO_DICT = refs["socio_data"]

    df_players = pd.read_csv(PLAYERS_FILE)
    if 'Squad' in df_players.columns and 'Club' not in df_players.columns:
        df_players['Club'] = df_players['Squad']
    df_players['Player_Search'] = df_players['Player'].apply(normalizar_texto)
    
    LISTA_CLUBES = list(CLUB_DICT.keys())
    print("✅ Braniac cargado y listo.")

except Exception as e:
    print(f"❌ Error crítico en tools.py: {e}")
    model = None; df_players = pd.DataFrame(); CLUB_DICT = {}; SOCIO_DICT = {}; feature_columns = []; LISTA_CLUBES = []

# ==========================================
# 2. MOTOR DE PREDICCIÓN
# ==========================================

def predecir_salario(jugador_row, target_club=None, target_league=None):
    if model is None: return {"error": "Modelo no cargado."}

    # Vector Base
    try:
        X_input = jugador_row[feature_columns].to_frame().T.copy()
        X_input = X_input.apply(pd.to_numeric, errors='coerce')
    except KeyError as e:
        missing = list(set(feature_columns) - set(jugador_row.index))
        return {"error": f"Faltan columnas: {missing}"}
    
    club_actual = jugador_row.get('Club', 'Desconocido')
    contexto_msg = f"Situación Actual en {club_actual}"
    
    masa_usada = jugador_row.get('Masa_Salarial_X', 0)
    tax_rate = jugador_row.get('Tax_Rate', 0.45)
    cov_factor = jugador_row.get('COV_Factor', 1.0)
    print(f"[DEBUG PRED] masa: {masa_usada}")
    print(f"[DEBUG PRED] tax_rate: {tax_rate}")
    print(f"[DEBUG PRED] cov_factor: {cov_factor}")

    # A. Modificación Club
    if target_club:
        club_encontrado = encontrar_coincidencia_difusa(target_club, LISTA_CLUBES)
        if club_encontrado:
            nueva_masa = CLUB_DICT[club_encontrado]
            X_input['Masa_Salarial_X'] = nueva_masa
            masa_usada = nueva_masa
            contexto_msg = f"Simulación: Fichaje por {club_encontrado.title()}"
        else:
            # Fallback directo
            club_key = target_club.lower().strip()
            nueva_masa = CLUB_DICT.get(club_key)
            if nueva_masa:
                X_input['Masa_Salarial_X'] = nueva_masa
                masa_usada = nueva_masa
                contexto_msg = f"Simulación: Fichaje por {target_club}"
            else:
                contexto_msg += f" (Club '{target_club}' no hallado, usando masa actual)"

    # B. Modificación Liga para evitar errores de entrada
    if target_league:
        mapa_paises = {
            'españa': 'La Liga', 'spain': 'La Liga', 'es': 'La Liga',
            'inglaterra': 'Premier League', 'uk': 'Premier League',
            'italia': 'Serie A', 'italy': 'Serie A',
            'alemania': 'Bundesliga', 'germany': 'Bundesliga',
            'francia': 'Ligue 1', 'france': 'Ligue 1'
        }
        league_key = target_league.lower().strip()
        nombre_liga = mapa_paises.get(league_key, target_league)
        
        socio_lower = {k.lower(): v for k, v in SOCIO_DICT.items()}
        datos_socio = socio_lower.get(nombre_liga.lower())
        
        if datos_socio:
            tax_rate = datos_socio['Tax_Rate']
            cov_factor = datos_socio['COV_Factor']
            
            if 'Tax_Rate' in X_input.columns: X_input['Tax_Rate'] = tax_rate
            if 'COV_Factor' in X_input.columns: X_input['COV_Factor'] = cov_factor
            
            col_liga_nueva = f"Comp_{nombre_liga}"
            for col in X_input.columns:
                if col.startswith("Comp_"): X_input[col] = 0
            if col_liga_nueva in feature_columns: X_input[col_liga_nueva] = 1
            
            if "Simulación" not in contexto_msg: contexto_msg = f"Simulación: Cambio a {nombre_liga}"
            else: contexto_msg += f" ({nombre_liga})"
        else:
            return {"error": f"No tengo datos fiscales para '{target_league}'."}

    # -----------------------------------------------------------------
    # 🚨🚨 ZONA DE DEPURACIÓN CRÍTICA 🚨🚨
    # -----------------------------------------------------------------
    
    # Predicción
    try:
        dmatrix = xgb.DMatrix(X_input, feature_names=feature_columns)
        log_pred = model.predict(dmatrix)[0]
        # 🚨 DEBUG PREDICCIÓN CRUDA 🚨
        print(f"[DEBUG PRED] Valor Logarítmico Crudo: {log_pred}")
        salario_bruto = np.exp(log_pred)
        print(f"[DEBUG PRED] Salario bruto: {salario_bruto}")
    except Exception as e:
        return {"error": f"Error matemático: {e}"}
    
    # Banda Neto
    rmse_log = 0.0569; z = 1.645
    neto_central = salario_bruto * (1 - tax_rate) * cov_factor
    print(f"[DEBUG PRED] neto central: {neto_central}")
    neto_min = np.exp(log_pred - (rmse_log * z)) * (1 - tax_rate) * cov_factor
    print(f"[DEBUG PRED] neto min: {neto_min}")
    neto_max = np.exp(log_pred + (rmse_log * z)) * (1 - tax_rate) * cov_factor
    print(f"[DEBUG PRED] neto max: {neto_max}")

    if neto_min < 0: neto_min = neto_central * 0.85
    
    return {
        "contexto": str(contexto_msg),
        "masa_salarial": float(masa_usada),
        "bruto_predicho": float(salario_bruto),
        "neto_min": float(neto_min),
        "neto_central": float(neto_central),
        "neto_max": float(neto_max),
        "tax_rate": float(tax_rate),
        "cov_factor": float(cov_factor)
    }

# ==========================================
# 3. HERRAMIENTA DE ANÁLISIS
# ==========================================

class PlayerContractAnalysis(BaseModel):
    player_name: str = Field(description="Nombre del jugador")
    analysis_type: str = Field(description="Tipo de análisis")
    executive_summary: str = Field(description="Resumen ejecutivo")
    financial_breakdown: str = Field(description="Desglose financiero")
    recommended_salary_range: str = Field(description="Rango neto recomendado")
    negotiation_strategy: str = Field(description="Estrategia sugerida")
    club_context: str = Field(description="Contexto del club")

def analyze_player_tool(player_name: str, client_openai=None, target_club: str = None, target_league: str = None, birth_year: int = None) -> dict:
    if df_players.empty: return {"error": "Base de datos no disponible."}
    
    matches = df_players[df_players['Player_Search'].str.contains(normalizar_texto(player_name), na=False)]
    if matches.empty: return {"error": f"Jugador '{player_name}' no encontrado."}
    
    if birth_year:
        try:
            anio_target = int(birth_year)
            matches_anio = matches[matches['Born'].between(anio_target - 1, anio_target + 1)]
            if not matches_anio.empty: matches = matches_anio
        except: pass
    
    player_row = matches.iloc[0]
    
    res = predecir_salario(player_row, target_club, target_league)
    if "error" in res: return res
    # 1. Definir el factor de escala (asumimos que el modelo predice en millones)
    SCALE_FACTOR = 1_000_000
    
    # 2. Multiplicar los valores predichos por el factor de escala
    #    para convertirlos de unidad (ej. millones) a valor real (euros).
    bruto_real = res['bruto_predicho'] * SCALE_FACTOR
    neto_min_real = res['neto_min'] * SCALE_FACTOR
    neto_max_real = res['neto_max'] * SCALE_FACTOR
    
    # 3. Formatear data_text usando los valores REALES (bruto_real, neto_min_real, etc.)
    data_text = f"""
    JUGADOR: {player_row['Player']}
    ESCENARIO: {res['contexto']}
    INPUTS: Masa €{res['masa_salarial']:,.0f} | Tax {res['tax_rate']*100:.1f}% | COV {res['cov_factor']:.2f}
    RESULTADOS: Bruto €{bruto_real:,.0f} | Neto €{neto_min_real:,.0f} - €{neto_max_real:,.0f}
    """
    print("\n[DEBUG IA] Datos Inyectados a la IA (data_text):\n", data_text)

    try:
        response = client_openai.beta.chat.completions.parse(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "Eres Braniac. Genera reporte."},
                {"role": "user", "content": data_text}
            ],
            response_format=PlayerContractAnalysis,
        )
        final_json = response.choices[0].message.parsed.model_dump()
        
        # Inyección de datos para mostrarlos claros 
        final_json['GCA90'] = f"{player_row.get('GCA_P90', 0):.2f}"
        final_json['SCA90'] = f"{player_row.get('SCA_P90', 0):.2f}"
        final_json['Def_P90'] = f"{player_row.get('Def_P90', 0):.2f}"
        final_json['Eficiencia'] = f"{player_row.get('Attack_Efficiency_Ratio', 0):.2f}"
        final_json['bruto_predicho_real'] = f"€{res['bruto_predicho']:,.0f}"
        final_json['neto_central_real'] = f"€{res['neto_central']:,.0f}"
        final_json['recommended_salary_range'] = f"€{res['neto_min']:,.0f} - €{res['neto_max']:,.0f}"
        final_json['masa_salarial_real'] = f"€{res['masa_salarial']:,.0f}"
        final_json['tax_rate_real'] = f"{res['tax_rate']*100:.1f}"
        final_json['cov_factor_real'] = f"{res['cov_factor']:.2f}"

        
        return final_json
    except Exception as e:
        return {"error": f"Error IA: {e}"}

# ==========================================
# 4. HERRAMIENTA DE CONSULTA LOOKUP
# ==========================================

def lookup_database_tool(category: str, name: str) -> dict:
    """Consulta rápida de datos estáticos."""
    key = name.lower().strip()
    
    if category == 'club':
        
        club_match = encontrar_coincidencia_difusa(name, LISTA_CLUBES)
        if club_match:
            masa = CLUB_DICT[club_match]
            return {"dato": f"Masa {club_match.title()}", "valor": f"€{masa:,.0f}"}
            
        
        masa = CLUB_DICT.get(key)
        if masa: return {"dato": f"Masa {name}", "valor": f"€{masa:,.0f}"}
        
        return {"error": f"Club '{name}' no encontrado."}
            
    elif category in ['country', 'league']:
        mapa = {'españa': 'La Liga', 'italia': 'Serie A', 'inglaterra': 'Premier League', 'alemania': 'Bundesliga', 'francia': 'Ligue 1'}
        search = mapa.get(key, name)
        socio_lower = {k.lower(): v for k, v in SOCIO_DICT.items()}
        res = socio_lower.get(search.lower())
        if res: return {"entidad": search, "tax_rate_real": f"{res['Tax_Rate']*100:.1f}", "cov_factor_real": f"{res['COV_Factor']:.2f}"}
        return {"error": f"Liga '{name}' no encontrada."}

    # CONSULTA DE RENDIMIENTO
    elif category == 'rendimiento':
        nombre_busqueda = normalizar_texto(name)
        matches = df_players[df_players['Player_Search'].str.contains(nombre_busqueda, na=False)]
        
        if matches.empty:
            return {"error": f"No encontré métricas para '{name}'."}
        
        p = matches.iloc[0]
        
        return {
            "jugador": p['Player'],
            "posicion": p.get('Pos', 'N/A'),
            "edad": int(p.get('Age', 0)),
            "equipo": p.get('Club', 'N/A'),
            # --- MÉTRICAS CLAVE ---
            "GCA90 (Goles Creados)": round(p.get('GCA_P90', 0), 2),
            "SCA90 (Creación Tiro)": round(p.get('SCA_P90', 0), 2),
            "Def_P90 (Acciones Defensivas)": round(p.get('Def_P90', 0), 2), 
            "Eficiencia Ofensiva": round(p.get('Attack_Efficiency_Ratio', 0), 2),
            "Wage/Club Ratio": round(p.get('Wage_Club_Ratio', 0), 4)
        }
    
    return {"error": "Categoría inválida."}

# ==========================================
# 5. DEFINICIÓN JSON-TOOLS
# ==========================================
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "analyze_player_tool",
            "description": "Calcula salario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {"type": "string"},
                    "birth_year": {"type": "integer"},
                    "target_club": {"type": "string"},
                    "target_league": {"type": "string"}
                },
                "required": ["player_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_database_tool",
            "description": "Consulta datos sueltos (Masa, Impuestos, Rendimiento).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string", 
                        "enum": ["club", "country", "rendimiento"],
                        "description": "Usa 'rendimiento' para buscar stats de jugador."
                    },
                    "name": {"type": "string"}
                },
                "required": ["category", "name"]
            }
        }
    }
]