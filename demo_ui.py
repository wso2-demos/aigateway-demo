#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import streamlit as st
import json
import yaml
import os
from dotenv import load_dotenv

# ------------------------------
# Localisation import
# ------------------------------
from localization import t, set_lang, get_lang

# ------------------------------
# Script para llamar a OpenAI vía WSO2
# ------------------------------

# Load environment variables from .env file
load_dotenv()

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Get global SSL/TLS setting
use_tls = config.get("USETLS", True)  # Default to True for security

# Load sensitive configuration from environment variables
def load_provider_env_config(provider_name):
    """Load provider configuration from environment variables"""
    return {
        "TOKEN_URL": os.getenv("WSO2_TOKEN_URL"),
        "CONSUMER_KEY": os.getenv("WSO2_CONSUMER_KEY"),
        "CONSUMER_SECRET": os.getenv("WSO2_CONSUMER_SECRET"),
        "CHAT_COMPLETIONS_URL": os.getenv(f"{provider_name.upper()}_CHAT_COMPLETIONS_URL")
    }

# Merge config.yaml with environment variables and filter enabled providers
for provider_name in config["providers"]:
    env_config = load_provider_env_config(provider_name)
    config["providers"][provider_name].update(env_config)

# Filter only enabled providers
enabled_providers = {name: config for name, config in config["providers"].items()
                    if config.get("ENABLED", True)}
config["providers"] = enabled_providers

def validate_provider_config(provider_config, required_fields, lang):
    missing = [field for field in required_fields if field not in provider_config or provider_config[field] is None]
    if missing:
        st.error(t('missing_fields', lang, fields=", ".join(missing)))
        st.error(t('env_config_help', lang))
        st.stop()



# ------------------------------
# Language selector (with fallback)
# ------------------------------
if hasattr(st, 'sidebar'):
    lang = st.sidebar.selectbox("🌐 Language / Idioma", ["en", "es"], format_func=lambda l: {"en": "English", "es": "Español"}[l])
else:
    lang = 'en'
set_lang(lang)

required_fields = ["TOKEN_URL", "CONSUMER_KEY", "CONSUMER_SECRET", "CHAT_COMPLETIONS_URL"]
for prov in config["providers"]:
    validate_provider_config(config["providers"][prov], required_fields, get_lang())

# Inicialización de contadores para todos los proveedores habilitados
provider_keys = list(config["providers"].keys())
if not provider_keys:
    st.error("No enabled providers found. Please check your config.yaml and .env files.")
    st.stop()
for prov in provider_keys:
    if f"{prov}_success" not in st.session_state:
        st.session_state[f"{prov}_success"] = 0
    if f"{prov}_error" not in st.session_state:
        st.session_state[f"{prov}_error"] = 0


# Banner superior con logo WSO2 y colores corporativos theme-aware
display_banner = f"""
<div class='wso2-banner'>
    <img src='https://wso2.cachefly.net/wso2/sites/all/image_resources/wso2-branding-logos/wso2-logo-orange.png' alt='WSO2 Logo' class='wso2-logo'>
    <span class='wso2-title'>{t('title')}</span>
</div>
"""
st.markdown(display_banner, unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Theme-aware banner styling */
    .wso2-banner {
        padding: 18px 0 10px 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--background-color);
        transition: background-color 0.2s ease;
    }

    .wso2-logo {
        height: 44px;
        margin-right: 24px;
    }

    .wso2-title {
        font-size: 2.2rem;
        font-weight: bold;
        letter-spacing: 1px;
        color: var(--text-color);
    }

    /* Light theme banner */
    @media (prefers-color-scheme: light) {
        .wso2-banner {
            background-color: #fff;
        }
        .wso2-title {
            color: #232323;
        }
    }

    /* Dark theme banner */
    @media (prefers-color-scheme: dark) {
        .wso2-banner {
            background-color: var(--background-color, #0e1117);
        }
        .wso2-title {
            color: #fff;
        }
    }

    /* Streamlit theme overrides for banner */
    .stApp[data-theme="light"] .wso2-banner {
        background-color: #fff;
    }

    .stApp[data-theme="light"] .wso2-title {
        color: #232323;
    }

    .stApp[data-theme="dark"] .wso2-banner {
        background-color: var(--background-color, #0e1117);
    }

    .stApp[data-theme="dark"] .wso2-title {
        color: #fff;
    }

    /* Theme-aware section title styling */
    .interaction-title {
        margin-bottom: 10px;
        color: var(--text-color);
        text-decoration: none !important;
        border: none !important;
        border-bottom: none !important;
        text-underline: none !important;
        box-shadow: none !important;
    }

    /* Override any default h3 styling that might add underlines */
    h3, .interaction-title {
        text-decoration: none !important;
        border-bottom: none !important;
        box-shadow: none !important;
        outline: none !important;
    }

    @media (prefers-color-scheme: light) {
        .interaction-title {
            color: #232323;
        }
    }

    @media (prefers-color-scheme: dark) {
        .interaction-title {
            color: #fff;
        }
    }

    .stApp[data-theme="light"] .interaction-title {
        color: #232323;
    }

    .stApp[data-theme="dark"] .interaction-title {
        color: #fff;
    }

    /* Theme-aware input styling */
    textarea, .stTextInput > div > input, .stTextArea > div > textarea {
        font-size: 1.1rem !important;
        font-family: inherit !important;
        border: 1.5px solid var(--text-color, #bbb) !important;
        border-radius: 7px !important;
        box-shadow: none !important;
        padding: 8px 10px !important;
        transition: border-color 0.2s ease !important;
    }

    textarea:focus, .stTextInput > div > input:focus, .stTextArea > div > textarea:focus {
        border-color: #FF5000 !important;
        box-shadow: 0 0 0 1px #FF5000 !important;
    }

    label, .stTextInput label, .stTextArea label {
        font-weight: bold !important;
        margin-bottom: 4px !important;
    }

    /* Light theme specific styles */
    @media (prefers-color-scheme: light) {
        textarea, .stTextInput > div > input, .stTextArea > div > textarea {
            background-color: #fff !important;
            color: #232323 !important;
            border-color: #bbb !important;
        }
        label, .stTextInput label, .stTextArea label {
            color: #232323 !important;
        }
    }

    /* Dark theme specific styles */
    @media (prefers-color-scheme: dark) {
        textarea, .stTextInput > div > input, .stTextArea > div > textarea {
            border-color: #666 !important;
        }
    }

    /* Streamlit theme class overrides */
    .stApp[data-theme="light"] textarea,
    .stApp[data-theme="light"] .stTextInput > div > input,
    .stApp[data-theme="light"] .stTextArea > div > textarea {
        background-color: #fff !important;
        color: #232323 !important;
        border-color: #bbb !important;
    }

    .stApp[data-theme="light"] label,
    .stApp[data-theme="light"] .stTextInput label,
    .stApp[data-theme="light"] .stTextArea label {
        color: #232323 !important;
    }

    .stApp[data-theme="dark"] textarea,
    .stApp[data-theme="dark"] .stTextInput > div > input,
    .stApp[data-theme="dark"] .stTextArea > div > textarea {
        border-color: #666 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    /* Theme-aware selectbox styling that works in both light and dark themes */
    .stSelectbox > div[data-baseweb="select"] {
        border: 2px solid var(--text-color, #333) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        min-height: 44px !important;
    }

    .stSelectbox > div[data-baseweb="select"]:hover {
        border-color: #FF5000 !important;
        box-shadow: 0 0 0 1px #FF5000 !important;
    }

    /* More specific selector for the selected value text */
    .stSelectbox > div[data-baseweb="select"] [role="combobox"] {
        font-weight: 600 !important;
        padding: 8px 12px !important;
        font-size: 16px !important;
        line-height: 1.4 !important;
    }

    /* Alternative selector for selected value */
    .stSelectbox > div[data-baseweb="select"] > div[data-baseweb="input"] {
        font-weight: 600 !important;
        padding: 8px 12px !important;
        font-size: 16px !important;
    }

    /* Ensure text is visible in selected state */
    .stSelectbox > div[data-baseweb="select"] span {
        font-weight: 600 !important;
        font-size: 16px !important;
        opacity: 1 !important;
        color: inherit !important;
    }

    .stSelectbox label {
        font-weight: 700 !important;
        font-size: 16px !important;
        margin-bottom: 8px !important;
    }

    /* Dark theme specific overrides */
    @media (prefers-color-scheme: dark) {
        .stSelectbox > div[data-baseweb="select"] {
            border-color: #666 !important;
        }

        .stSelectbox label {
            color: #fff !important;
        }

        .stSelectbox > div[data-baseweb="select"] [role="combobox"],
        .stSelectbox > div[data-baseweb="select"] span {
            color: #fff !important;
        }
    }

    /* Streamlit dark theme class overrides */
    .stApp[data-theme="dark"] .stSelectbox > div[data-baseweb="select"] {
        border-color: #666 !important;
        background-color: var(--background-color) !important;
    }

    .stApp[data-theme="dark"] .stSelectbox label {
        color: #fff !important;
    }

    .stApp[data-theme="dark"] .stSelectbox > div[data-baseweb="select"] [role="combobox"],
    .stApp[data-theme="dark"] .stSelectbox > div[data-baseweb="select"] span {
        color: #fff !important;
    }

    /* Light theme text color */
    .stApp[data-theme="light"] .stSelectbox > div[data-baseweb="select"] [role="combobox"],
    .stApp[data-theme="light"] .stSelectbox > div[data-baseweb="select"] span {
        color: #232323 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<hr style='margin:0 0 20px 0;border:1px solid #FF5000;'>", unsafe_allow_html=True)


# Contadores dinámicos con look WSO2 para todos los proveedores definidos en el YAML
cols = st.columns(len(provider_keys))
for idx, prov in enumerate(provider_keys):
    cols[idx].markdown(f"""
    <div style='color:#FF5000;font-size:1.1rem;font-weight:bold;'>{t('success_count', provider=prov, count=st.session_state.get(f'{prov}_success', 0))}</div>
    <div style='color:#d32f2f;font-size:1.1rem;font-weight:bold;'>{t('error_count', provider=prov, count=st.session_state.get(f'{prov}_error', 0))}</div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin:20px 0 20px 0;border:1px solid #FF5000;'>", unsafe_allow_html=True)


# Sección de interacción
titulo_interaccion = f"<div class='interaction-title' style='font-size:1.5rem;font-weight:bold;margin:20px 0 10px 0;'>{t('select_and_ask')}</div>"
st.markdown(titulo_interaccion, unsafe_allow_html=True)

# Select dinámico de proveedores y etiquetas
if provider_keys:
    provider = st.selectbox(t('select_provider'), provider_keys, index=0)
else:
    st.error("No providers available")
    st.stop()
provider_config = config["providers"][provider]

# Acceso a los valores de configuración
TOKEN_URL = provider_config["TOKEN_URL"]
CONSUMER_KEY = provider_config["CONSUMER_KEY"]
CONSUMER_SECRET = provider_config["CONSUMER_SECRET"]
CHAT_COMPLETIONS_URL = provider_config["CHAT_COMPLETIONS_URL"]


question_label = t('ask_question', provider=provider)
answer_label = t('response_from', provider=provider)

model = provider_config.get("MODEL", "")


default_question = t('default_question')
user_question = st.text_area(question_label, value=default_question, height=100)

st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

if st.button(t('send'), type="primary"):
    # Paso 1: Obtener el access token automáticamente
    try:
        token_data = {
            "grant_type": "client_credentials"
        }
        print(f"[LOG] Requesting token from: {TOKEN_URL} with client_id: {CONSUMER_KEY}")
        token_response = requests.post(
            TOKEN_URL,
            data=token_data,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            verify=use_tls
        )
        print(f"[LOG] Token response status: {token_response.status_code}")
        print(f"[LOG] Token response body: {token_response.text}")
        if token_response.status_code == 200:
            access_token = token_response.json().get("access_token")
            if not access_token:
                print("[ERROR] No access token in response!")
                st.error(t('no_access_token'))
                st.error(f"Server response: {token_response.text}")
                st.stop()
        else:
            print(f"[ERROR] Token request failed: {token_response.text}")
            st.error(t('token_error', status=token_response.status_code))
            st.error(f"Server response: {token_response.text}")
            st.stop()
        # Paso 2: Hacer la llamada a la API con el token obtenido
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": user_question
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        payload_str = json.dumps(payload, ensure_ascii=False)
        print(f"[LOG] JSON payload sent to model API:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
        print(f"[LOG] Sending request to: {CHAT_COMPLETIONS_URL}")
        print(f"[LOG] Request headers: {headers}")
        print(f"[LOG] Request payload: {payload_str}")
        api_response = requests.post(
            CHAT_COMPLETIONS_URL,
            headers=headers,
            data=payload_str,
            verify=use_tls
        )
        print(f"[LOG] API response status: {api_response.status_code}")
        print(f"[LOG] API response body: {api_response.text}")
        if api_response.status_code == 200:
            st.session_state[f"{provider}_success"] += 1
            try:
                result = api_response.json()
                print(f"[LOG] API response JSON: {result}")
                content = None
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                st.session_state[f"last_response_{provider}"] = content or str(result)
            except Exception as ex:
                print(f"[ERROR] Exception parsing API response JSON: {ex}")
                st.session_state[f"last_response_{provider}"] = api_response.text
            st.rerun()
        else:
            st.session_state[f"{provider}_error"] += 1
            try:
                error_json = api_response.json()
                print(f"[ERROR] API error JSON: {error_json}")
                if isinstance(error_json, dict) and str(error_json.get("code")) == "900514":
                    # Mostrar el motivo real del bloqueo
                    reason = None
                    if (
                        "message" in error_json
                        and isinstance(error_json["message"], dict)
                        and "assessments" in error_json["message"]
                    ):
                        assessments = error_json["message"]["assessments"]
                        if isinstance(assessments, dict) and "invalidUrls" in assessments:
                            invalid_urls = ", ".join(assessments["invalidUrls"])
                            reason = t('blocked_url', urls=invalid_urls)
                        elif isinstance(assessments, str):
                            reason = assessments
                    # Si no hay assessments, intenta mostrar actionReason o el mensaje original
                    if not reason:
                        if (
                            "message" in error_json
                            and isinstance(error_json["message"], dict)
                            and "actionReason" in error_json["message"]
                        ):
                            reason = error_json["message"]["actionReason"]
                        elif "message" in error_json and "description" in error_json:
                            reason = str(error_json["message"] +  " : " + error_json["description"])
                        elif "message" in error_json:
                            reason = str(error_json["message"])
                        else:
                            reason = str(error_json)
                    st.session_state[f"last_response_{provider}"] = reason
                else:
                    st.session_state[f"last_response_{provider}"] = api_response.text
            except Exception as ex:
                print(f"[ERROR] Exception parsing API error JSON: {ex}")
                st.session_state[f"last_response_{provider}"] = t('unknown_error')
            st.rerun()
    except Exception as e:
        print(f"[ERROR] Exception in main request flow: {e}")
        st.session_state[f"{provider}_error"] += 1
        st.session_state[f"last_response_{provider}"] = t('api_request_error', error=str(e))
        st.rerun()

# Mostrar la última respuesta si existe (después del botón)
if f"last_response_{provider}" in st.session_state:
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.text_area(answer_label, value=st.session_state[f"last_response_{provider}"], height=200)

