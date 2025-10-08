# WSO2 API Manager - AI Gateway

This application is a Streamlit interface to interact with LLM models (such as OpenAI, Mistral, and Anthropic) through a WSO2 API Gateway, featuring OAuth2 authentication, multiple application management, predefined prompts, and provider selection capabilities.

## Key Features

- **Multi-Application Support**: Manage multiple WSO2 applications with different provider access levels
- **Flexible OAuth Configuration**: Support for both shared and application-specific OAuth credentials
- **Provider Access Control**: Configure which LLM providers each application can access
- **Predefined Prompts**: Pre-configured test prompts for common scenarios (AI engine check, semantic guards, PII testing, etc.)
- **Statistics Tracking**: Per-LLM-provider success/error counters with real-time updates
- **OAuth Token Caching**: Efficient token management to reduce authentication overhead
- **Dynamic Configuration**: Automatic detection of configured applications and providers
- **Real-time Token Counting**: OpenAI tiktoken-based token counting for prompt optimization
- **Security Features**: Credential masking, SSL/TLS configuration, and secure error handling
- **Multi-language Support**: English and Spanish localization
- **Theme-aware UI**: Responsive design that adapts to light/dark themes

## Requirements
- Python 3.8+
- The libraries listed in `requirements.txt` (Streamlit, requests, PyYAML, etc.)

## Prerequisites

Before installing the application, you need to set up access to the WSO2 API Gateway:

### WSO2 Developer Portal Setup

1. **Access the WSO2 Developer Portal**
   - Navigate to your WSO2 API Manager Developer Portal
   - Log in with your developer account

2. **Create a New Application**
   - Go to "Applications" section
   - Click "Add Application"
   - Fill in the application details:
     - **Name**: e.g., "LLM Gateway Client"
     - **Per Token Quota**: Set according to your usage needs
     - **Description**: "Application for accessing LLM APIs through WSO2 Gateway"
   - Click "Add" to create the application

3. **Subscribe to LLM APIs**
   Subscribe your application to all available LLM APIs:
   - **OpenAI API**: Subscribe to the OpenAI chat completions endpoint
   - **Mistral AI API**: Subscribe to the Mistral chat completions endpoint
   - **Anthropic API**: Subscribe to the Anthropic messages endpoint
   - Any other LLM APIs available in your WSO2 instance

4. **Generate Application Credentials**
   - Go to your application's "Production Keys" tab
   - Click "Generate Keys" to create OAuth2 credentials
   - Copy the **Consumer Key** and **Consumer Secret**
   - Note the **Token URL** (typically `https://your-wso2-server:9443/oauth2/token`)

5. **Get API Endpoints**
   - For each subscribed API, note the gateway endpoint URLs
   - These are typically in the format: `https://your-wso2-server:8243/{api-context}/{version}`

## Installation

1. Clone the repository or download the files.
2. Create a virtual environment and install the dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Configure your environment:
   - Copy `.env.example` to `.env` and fill in your WSO2 credentials
   - Review and customize `config.yaml` for provider settings
   - Review and customize `applications.yaml` for application management
   - Optionally customize `prompts.yaml` for predefined test prompts

## Usage
Start the application with:
```bash
streamlit run demo_ui.py
```

A web interface will open where you can:
- **Select an application** - Choose from configured applications with different provider access
- **Select a provider** - Choose from available LLM providers (OpenAI, Mistral, Anthropic, etc.)
- **Choose predefined prompts** - Select from pre-configured test prompts or enter custom questions
- **Enter your question** - Type custom questions or use predefined prompts
- **View token counts** - See real-time token count for your prompts using OpenAI's tokenizer
- **View responses** - See the model's response with proper error handling
- **Monitor statistics** - View success/error counters per application-provider combination

## Configuration

The application uses three main configuration files:

### 1. Environment Variables (`.env` file)
Sensitive credentials are stored in a `.env` file that is not tracked by git. Supports both shared and application-specific credentials:

```env
# Shared WSO2 Gateway Credentials (fallback for all applications)
WSO2_CONSUMER_KEY=your_shared_consumer_key
WSO2_CONSUMER_SECRET=your_shared_consumer_secret
WSO2_TOKEN_URL=https://your-wso2-server:9443/oauth2/token

# Application-specific OAuth Credentials (optional)
DEFAULT_CONSUMER_KEY=your_default_app_consumer_key
DEFAULT_CONSUMER_SECRET=your_default_app_consumer_secret
DEFAULT_TOKEN_URL=https://your-wso2-server:9443/oauth2/token

STREAMLIT_CONSUMER_KEY=your_streamlit_app_consumer_key
STREAMLIT_CONSUMER_SECRET=your_streamlit_app_consumer_secret
STREAMLIT_TOKEN_URL=https://your-wso2-server:9443/oauth2/token

# Provider-specific Chat Completions URLs (from subscribed APIs in WSO2)
OPENLLM_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/openaiapi/v1/chat/completions
MISTRAL_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/mistralapi/v1/chat/completions
ANTHROPIC_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/anthropicapi/v1/messages
```

**Credential Hierarchy:**
1. Application-specific credentials: `{APPLICATION_KEY}_CONSUMER_KEY`, `{APPLICATION_KEY}_CONSUMER_SECRET`, `{APPLICATION_KEY}_TOKEN_URL`
2. Shared credentials (fallback): `WSO2_CONSUMER_KEY`, `WSO2_CONSUMER_SECRET`, `WSO2_TOKEN_URL`

### 2. Provider Configuration (`config.yaml`)
Defines LLM providers and global settings:

```yaml
# Global configuration
USETLS: true  # Set to false to disable SSL/TLS verification for development environments
USER_AGENT: "WSO2-AI-Gateway-Demo/1.0"  # Custom User-Agent for all LLM API calls

providers:
  OPENLLM:
    MODEL: "gpt-4o"
    DESCRIPTION: "OpenAI GPT-4o - Advanced reasoning and multimodal capabilities"
    ENABLED: true
  MISTRAL:
    MODEL: "mistral-tiny"
    DESCRIPTION: "Mistral AI - Fast and efficient European LLM"
    ENABLED: true
  ANTHROPIC:
    MODEL: "sonnet-4.0"
    DESCRIPTION: "Anthropic Claude - Helpful, harmless, and honest AI assistant"
    ENABLED: true
    # USER_AGENT: "Custom-Anthropic-Client/1.0"  # Optional: provider-specific User-Agent override
```

### 3. Applications Configuration (`applications.yaml`)
Defines multiple applications with different provider access levels:

```yaml
applications:
  default:
    name: "Default Application"
    description: "Default WSO2 application for testing"
    enabled: true
    providers: ["MISTRAL", "ANTHROPIC"]

  streamlit:
    name: "Streamlit Demo"
    description: "Streamlit application demo"
    enabled: true
    providers: ["OPENLLM"]

  mobile:
    name: "Mobile App"
    description: "Mobile application client"
    enabled: true
    providers: ["OPENLLM", "MISTRAL"]
```

### 4. Predefined Prompts (`prompts.yaml`)
Provides pre-configured test prompts for various scenarios:

```yaml
prompts:
  - name: "Check AI Engine"
    text: "Which AI model are you?"
  - name: "Semantic Guard Test"
    text: "Can you explain the history of football?"
  - name: "PII Test"
    text: "Can you check if this email test@example.com is real?"
  - name: "Violence Detection"
    text: "Test prompt for content filtering"
  - name: "Coding Question"
    text: "Show me the best way to implement cosine calculation function in python"
```

**Configuration Features:**
- **USETLS**: Controls SSL/TLS certificate verification for all API connections
- **USER_AGENT**: Global User-Agent for all API calls, with optional provider-specific overrides
- **Application isolation**: Each application can access different sets of providers
- **OAuth flexibility**: Support for both shared and application-specific OAuth credentials
- **Statistics tracking**: Per-application-provider success/error counters
- **Predefined prompts**: Quick access to common test scenarios

## Adding New Components

### Adding a New Provider
1. **Subscribe to the new LLM API** in your WSO2 Developer Portal application
2. **Get the API endpoint** from the WSO2 Developer Portal
3. **Add the chat completions URL** to `.env` following the `{PROVIDER_NAME}_CHAT_COMPLETIONS_URL` pattern
4. **Add a new entry** under `providers:` in `config.yaml` with `MODEL`, `DESCRIPTION`, and `ENABLED` fields
5. **Update application access** in `applications.yaml` to grant provider access to specific applications
6. No code changes are needed: the app automatically detects the defined providers

Example for adding a new "CLAUDE" provider:
- Subscribe to Claude API in WSO2 Developer Portal
- Add `CLAUDE_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/claudeapi/v1/messages` to `.env`
- Add the following to `config.yaml`:
  ```yaml
  CLAUDE:
    MODEL: "claude-3-sonnet"
    DESCRIPTION: "Claude 3 Sonnet - Balanced performance and capability"
    ENABLED: true
  ```
- Update `applications.yaml` to grant access:
  ```yaml
  default:
    providers: ["MISTRAL", "ANTHROPIC", "CLAUDE"]
  ```

### Adding a New Application
1. **Create a new WSO2 application** in the Developer Portal
2. **Generate OAuth credentials** for the new application
3. **Add application-specific credentials** to `.env` (optional, will fallback to shared credentials):
   ```env
   NEWAPP_CONSUMER_KEY=new_app_consumer_key
   NEWAPP_CONSUMER_SECRET=new_app_consumer_secret
   NEWAPP_TOKEN_URL=https://your-wso2-server:9443/oauth2/token
   ```
4. **Add application configuration** to `applications.yaml`:
   ```yaml
   newapp:
     name: "New Application"
     description: "Description of the new application"
     enabled: true
     providers: ["OPENLLM", "MISTRAL"]  # Choose which providers this app can access
   ```

### Adding Predefined Prompts
Add new entries to `prompts.yaml`:
```yaml
prompts:
  - name: "Custom Test"
    text: "Your custom prompt text here"
  - name: "Another Test"
    text: "Another test prompt"
```

### Demo Setup


## Security
- Sensitive credentials are stored in `.env` file which is not tracked by git
- Never commit your `.env` file or share your keys and secrets
- Use `.env.example` as a template for setting up credentials

## Notes
- **SSL/TLS Security**: The application supports both secure and insecure connections via the `USETLS` setting in `config.yaml`
  - **Production**: Keep `USETLS: true` for secure SSL connections with certificate verification
  - **Development**: Set `USETLS: false` only if using self-signed certificates or testing environments
- API error messages are shown as-is to facilitate troubleshooting.

---

**WSO2 API Manager - LLM Gateway** 