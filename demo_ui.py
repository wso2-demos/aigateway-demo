#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import streamlit as st
import json
import yaml
import os
from dotenv import load_dotenv
import tiktoken

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

# Load prompts configuration
with open("prompts.yaml", "r") as f:
    prompts_config = yaml.safe_load(f)

# Load applications configuration
with open("applications.yaml", "r") as f:
    applications_config = yaml.safe_load(f)
    # Filter only enabled applications and get available application keys
    enabled_applications = { key: app_config for key, app_config in applications_config ["applications"].items()                       
    if app_config.get("enabled", True)} 
    applications_config["applications"] = enabled_applications
    # Get available applications
    application_keys = list(applications_config["applications"].keys())
    if not application_keys:
        print("ERROR: No applications are configured or enabled.")
        exit(1)

# Security helper functions
def mask_sensitive_data(text, mask_char="*", visible_chars=4):
    """Mask sensitive data showing only first and last few characters"""
    if not text or len(text) <= visible_chars * 2:
        return mask_char * 8
    return f"{text[:visible_chars]}{mask_char * 8}{text[-visible_chars:]}"

def sanitize_headers_for_logging(headers):
    """Remove or mask sensitive headers for logging"""
    safe_headers = headers.copy()
    if 'Authorization' in safe_headers:
        auth_parts = safe_headers['Authorization'].split(' ')
        if len(auth_parts) > 1:
            safe_headers['Authorization'] = f"{auth_parts[0]} {mask_sensitive_data(auth_parts[1])}"
    return safe_headers

def count_tokens(text, model_name="gpt-4"):
    """Count tokens in text using OpenAI's tiktoken library"""
    try:
        # Map common model names to tiktoken encodings
        model_mapping = {
            "gpt-4": "cl100k_base",
            "gpt-4o": "cl100k_base",
            "gpt-3.5-turbo": "cl100k_base",
            "text-davinci-003": "p50k_base",
            "text-davinci-002": "p50k_base"
        }

        # Default to cl100k_base for most modern models
        encoding_name = model_mapping.get(model_name.lower(), "cl100k_base")
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"[WARNING] Token counting failed: {e}")
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

# Get global SSL/TLS setting
use_tls = config.get("USETLS", True)  # Default to True for security

# Security warning for demo operator
if not use_tls:
    print("⚠️  [SECURITY WARNING] SSL/TLS verification is DISABLED. This is insecure and should only be used for localhost/demo purposes!")
else:
    print("🔒 [SECURITY] SSL/TLS verification is ENABLED. Connections are secure.")

# Load sensitive configuration from environment variables
def load_application_env_config(application_key):
    """Load application-specific OAuth configuration from environment variables"""
    # Application-specific OAuth credentials (with fallback to shared credentials)
    app_consumer_key = os.getenv(f"{application_key.upper()}_CONSUMER_KEY")
    app_consumer_secret = os.getenv(f"{application_key.upper()}_CONSUMER_SECRET")
    app_token_url = os.getenv(f"{application_key.upper()}_TOKEN_URL")

    # Use application-specific credentials if available, otherwise fall back to shared
    consumer_key = app_consumer_key or os.getenv("WSO2_CONSUMER_KEY")
    consumer_secret = app_consumer_secret or os.getenv("WSO2_CONSUMER_SECRET")
    token_url = app_token_url or os.getenv("WSO2_TOKEN_URL")

    return {
        "TOKEN_URL": token_url,
        "CONSUMER_KEY": consumer_key,
        "CONSUMER_SECRET": consumer_secret,
        # Store original OAuth provider identifier for token caching
        "OAUTH_PROVIDER": f"{consumer_key}:{token_url}" if consumer_key and token_url else None
    }

def load_provider_env_config(provider_name):
    """Load provider configuration from environment variables"""
    return {
        "CHAT_COMPLETIONS_URL": os.getenv(f"{provider_name.upper()}_CHAT_COMPLETIONS_URL"),
    }

# Merge config.yaml with environment variables and filter enabled providers
for provider_name in config["providers"]:
    env_config = load_provider_env_config(provider_name)
    config["providers"][provider_name].update(env_config)

# Filter only enabled providers
enabled_providers = {name: config for name, config in config["providers"].items()
                    if config.get("ENABLED", True)}
config["providers"] = enabled_providers

# Filter only enabled applications
enabled_applications = {key: app_config for key, app_config in applications_config["applications"].items()
                       if app_config.get("enabled", True)}
applications_config["applications"] = enabled_applications

# OAuth token cache - stores tokens per OAuth provider
oauth_token_cache = {}

def get_oauth_provider_key(provider_config):
    """Generate a unique key for OAuth provider identification"""
    return provider_config.get("OAUTH_PROVIDER", "default")

def get_cached_token(oauth_provider_key):
    """Get cached OAuth token if still valid"""
    if oauth_provider_key in oauth_token_cache:
        token_info = oauth_token_cache[oauth_provider_key]
        # Simple check - in production, you'd check expiration time
        if token_info.get("access_token"):
            return token_info["access_token"]
    return None

def cache_token(oauth_provider_key, token_response):
    """Cache OAuth token response"""
    if token_response and "access_token" in token_response:
        oauth_token_cache[oauth_provider_key] = {
            "access_token": token_response["access_token"],
            "token_type": token_response.get("token_type", "Bearer"),
            "expires_in": token_response.get("expires_in"),
            # In production, store actual expiration timestamp
        }
        print(f"[LOG] Cached token for OAuth provider: {oauth_provider_key}")

def acquire_oauth_token(application_config):
    """Acquire OAuth token for the application, using cache when possible"""
    oauth_provider_key = get_oauth_provider_key(application_config)

    # Try to use cached token first
    cached_token = get_cached_token(oauth_provider_key)
    if cached_token:
        print(f"[LOG] Using cached token for OAuth provider: {oauth_provider_key}")
        return cached_token

    # Request new token
    token_url = application_config["TOKEN_URL"]
    consumer_key = application_config["CONSUMER_KEY"]
    consumer_secret = application_config["CONSUMER_SECRET"]

    token_data = {
        "grant_type": "client_credentials"
    }

    print(f"[LOG] Requesting new token from: {token_url} with client_id: {consumer_key}")
    token_response = requests.post(
        token_url,
        data=token_data,
        auth=HTTPBasicAuth(consumer_key, consumer_secret),
        verify=use_tls
    )

    print(f"[LOG] Token response status: {token_response.status_code}")
    if token_response.status_code == 200:
        token_json = token_response.json()
        access_token = token_json.get("access_token")
        if not access_token:
            print("[ERROR] No access token in response!")
            raise Exception(t('no_access_token'))

        # Cache the token
        cache_token(oauth_provider_key, token_json)
        print(f"[LOG] Access token acquired successfully for OAuth provider: {oauth_provider_key}")
        return access_token
    else:
        print(f"[ERROR] Token request failed with status: {token_response.status_code}")
        raise Exception(t('token_error', status=token_response.status_code))

def validate_provider_config(provider_config, required_fields):
    missing = [field for field in required_fields if field not in provider_config or provider_config[field] is None]
    if missing:
        st.error(t('missing_fields', fields=", ".join(missing)))
        st.error(t('env_config_help'))
        st.stop()

def validate_application_config(application_config, required_fields):
    missing = [field for field in required_fields if field not in application_config or application_config[field] is None]
    if missing:
        st.error(t('missing_fields', fields=", ".join(missing)))
        st.error(t('env_config_help'))
        st.stop()


# Get available applications
application_keys = list(applications_config["applications"].keys())
if not application_keys:
    st.error(t('no_applications_available'))
    st.stop()

# ------------------------------
# Language selector (with fallback)
# ------------------------------
if hasattr(st, 'sidebar'):
    lang = st.sidebar.selectbox("🌐 Language / Idioma", ["en", "es"], format_func=lambda l: {"en": "English", "es": "Español"}[l])
    selected_app = st.sidebar.selectbox(
        t('select_application'),
        application_keys,
        format_func=lambda app_key: applications_config["applications"][app_key]["name"]
    )
else:
    lang = 'en'
    selected_app = application_keys[0] if application_keys else None
set_lang(lang)

# Get selected application configuration
if not selected_app:
    st.error(t('no_applications_available'))
    st.stop()

selected_app_config = applications_config["applications"][selected_app]
app_oauth_config = load_application_env_config(selected_app)

# Validate application OAuth configuration
app_required_fields = ["TOKEN_URL", "CONSUMER_KEY", "CONSUMER_SECRET"]
validate_application_config(app_oauth_config, app_required_fields)

# Filter providers available to this application
available_provider_keys = []
if "providers" in selected_app_config:
    for provider in selected_app_config["providers"]:
        if provider in config["providers"]:
            available_provider_keys.append(provider)

if not available_provider_keys:
    st.error(t('no_providers_for_app'))
    st.stop()

# Validate provider configurations
provider_required_fields = ["CHAT_COMPLETIONS_URL"]
for prov in config["providers"]:
    validate_provider_config(config["providers"][prov], provider_required_fields)

# Check if we have applications configured
if not applications_config["applications"]:
    st.error(t('no_applications_available'))
    st.stop()



# Initialize session state for application-provider statistics\ndef init_session_stats():\n    \"\"\"Initialize session state counters for all application-provider combinations\"\"\"\n    for app_key in application_keys:\n        app_config = applications_config[\"applications\"][app_key]\n        if \"providers\" in app_config:\n            for provider in app_config[\"providers\"]:\n                if provider in config[\"providers\"]:\n                    success_key = f\"{app_key}_{provider}_success\"\n                    error_key = f\"{app_key}_{provider}_error\"\n                    if success_key not in st.session_state:\n                        st.session_state[success_key] = 0\n                    if error_key not in st.session_state:\n                        st.session_state[error_key] = 0\n\ninit_session_stats()\n\n# Banner superior con logo WSO2 y colores corporativos theme-aware
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
cols = st.columns(len(available_provider_keys))
for idx, prov in enumerate(available_provider_keys):
    cols[idx].markdown(f"""
    <div style='color:#FF5000;font-size:1.1rem;font-weight:bold;'>{t('success_count', provider=prov, count=st.session_state.get(f'{selected_app}_{prov}_success', 0))}</div>
    <div style='color:#d32f2f;font-size:1.1rem;font-weight:bold;'>{t('error_count', provider=prov, count=st.session_state.get(f'{selected_app}_{prov}_error', 0))}</div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin:20px 0 20px 0;border:1px solid #FF5000;'>", unsafe_allow_html=True)


# Sección de interacción
titulo_interaccion = f"<div class='interaction-title' style='font-size:1.5rem;font-weight:bold;margin:20px 0 10px 0;'>{t('select_and_ask')}</div>"
st.markdown(titulo_interaccion, unsafe_allow_html=True)

# Select dinámico de proveedores y etiquetas
if available_provider_keys:
    provider = st.selectbox(t('select_provider'), available_provider_keys, index=0)
else:
    st.error("No providers available for this application")
    st.stop()
provider_config = config["providers"][provider]

# Provider configuration is now loaded dynamically
CHAT_COMPLETIONS_URL = provider_config["CHAT_COMPLETIONS_URL"]


question_label = t('ask_question', provider=provider)
answer_label = t('response_from', provider=provider)

model = provider_config.get("MODEL", "")

# Prompt selection dropdown
prompt_options = [prompt['name'] for prompt in prompts_config['prompts']]
selected_prompt = st.selectbox(t('select_prompt'), prompt_options, index=0)

# Get the text for the selected prompt
selected_prompt_text = ""
for prompt in prompts_config['prompts']:
    if prompt['name'] == selected_prompt:
        selected_prompt_text = prompt['text']
        break

# Use selected prompt text or fallback to default
if selected_prompt_text:
    default_question = selected_prompt_text
else:
    default_question = t('default_question')

user_question = st.text_area(question_label, value=default_question, height=100, max_chars=5000)

# Display token count
if user_question:
    token_count = count_tokens(user_question, model)
    st.markdown(f"<div style='color:#666; font-size:0.9rem; margin-top:5px; margin-bottom:15px;'>{t('token_count', count=token_count)}</div>", unsafe_allow_html=True)
else:
    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

if st.button(t('send'), type="primary"):
    # Basic input validation
    if not user_question or not user_question.strip():
        st.error(t('empty_question_error'))
        st.stop()

    if len(user_question) > 5000:
        st.error(t('question_too_long', max_length=5000))
        st.stop()
    # Paso 1: Obtener el access token automáticamente
    try:
        access_token = acquire_oauth_token(app_oauth_config)
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
        print(f"[LOG] Request headers: {sanitize_headers_for_logging(headers)}")
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
            success_key = f"{selected_app}_{provider}_success"
            if success_key not in st.session_state:
                st.session_state[success_key] = 0
            st.session_state[success_key] += 1
            try:
                result = api_response.json()
                print(f"[LOG] API response JSON: {result}")
                content = None
                if "choices" in result and result["choices"]:
                    content = result["choices"][0]["message"]["content"]
                st.session_state[f"last_response_{selected_app}_{provider}"] = content or str(result)
            except Exception as ex:
                print(f"[ERROR] Exception parsing API response JSON: {ex}")
                st.session_state[f"last_response_{selected_app}_{provider}"] = api_response.text
            st.rerun()
        else:
            error_key = f"{selected_app}_{provider}_error"
            if error_key not in st.session_state:
                st.session_state[error_key] = 0
            st.session_state[error_key] += 1
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
                    st.session_state[f"last_response_{selected_app}_{provider}"] = reason
                else:
                    st.session_state[f"last_response_{selected_app}_{provider}"] = api_response.text
            except Exception as ex:
                print(f"[ERROR] Exception parsing API error JSON: {ex}")
                st.session_state[f"last_response_{selected_app}_{provider}"] = t('unknown_error')
            st.rerun()
    except Exception as e:
        print(f"[ERROR] Exception in main request flow: {e}")
        error_key = f"{selected_app}_{provider}_error"
        if error_key not in st.session_state:
            st.session_state[error_key] = 0
        st.session_state[error_key] += 1
        # Handle OAuth-specific errors differently
        error_message = str(e)
        if "token" in error_message.lower() or "oauth" in error_message.lower():
            st.session_state[f"last_response_{selected_app}_{provider}"] = f"OAuth Error: {error_message}"
        else:
            st.session_state[f"last_response_{selected_app}_{provider}"] = t('api_request_error', error=error_message)
        st.rerun()

# Mostrar la última respuesta si existe (después del botón)
if f"last_response_{selected_app}_{provider}" in st.session_state:
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.text_area(answer_label, value=st.session_state[f"last_response_{selected_app}_{provider}"], height=200)

