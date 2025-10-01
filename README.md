# WSO2 API Manager - AI Gateway

This application is a Streamlit interface to interact with LLM models (such as OpenAI and Mistral) through a WSO2 API Gateway, handling OAuth2 authentication and allowing you to dynamically select the AI provider.

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
   - Copy `.env.example` to `.env`
   - Fill in your WSO2 credentials obtained from the Developer Portal
   - The `config.yaml` file contains public configuration (models, etc.)

## Usage
Start the application with:
```bash
streamlit run demo_ui.py
```

A web interface will open where you can:
- Select the provider (OpenAI, Mistral, etc.)
- Enter your question
- View the model's response
- See counters for successful and failed calls per provider

## Configuration

### Environment Variables (`.env` file)
Sensitive credentials are stored in a `.env` file that is not tracked by git. Use the credentials and URLs obtained from your WSO2 Developer Portal setup:

```env
# WSO2 Gateway Shared Credentials (from your application in WSO2 Developer Portal)
WSO2_CONSUMER_KEY=your_consumer_key_from_wso2_app
WSO2_CONSUMER_SECRET=your_consumer_secret_from_wso2_app
WSO2_TOKEN_URL=https://your-wso2-server:9443/oauth2/token

# Provider-specific Chat Completions URLs (from subscribed APIs in WSO2)
OPENAI_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/openaiapi/v1/chat/completions
MISTRAL_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/mistralapi/v1/chat/completions
ANTHROPIC_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/anthropicapi/v1/messages
```

**How to fill in these values:**
1. **WSO2_CONSUMER_KEY & WSO2_CONSUMER_SECRET**: Copy from your WSO2 application's "Production Keys" section
2. **WSO2_TOKEN_URL**: Use your WSO2 server's OAuth2 token endpoint
3. **Chat Completions URLs**: Copy the gateway URLs from each subscribed API in the WSO2 Developer Portal

### Public Configuration (`config.yaml`)
The `config.yaml` file contains non-sensitive application and provider settings:

```yaml
# Global configuration
USETLS: true  # Set to false to disable SSL/TLS verification for development environments

providers:
  OPENAI:
    MODEL: "gpt-4o"
    ENABLED: true
  MISTRAL:
    MODEL: "mistral-tiny"
    ENABLED: true
```

**Configuration Options:**
- **USETLS**: Controls SSL/TLS certificate verification for all API connections
  - `true` (recommended): Enables secure SSL connections with certificate verification
  - `false`: Disables SSL verification (use only in development environments with self-signed certificates)

### Required environment variables
- `WSO2_CONSUMER_KEY` and `WSO2_CONSUMER_SECRET`: Shared OAuth2 credentials for all providers
- `WSO2_TOKEN_URL`: OAuth2 endpoint to obtain the token
- `{PROVIDER}_CHAT_COMPLETIONS_URL`: Provider-specific chat completions endpoint

### Adding a new provider
1. **Subscribe to the new LLM API** in your WSO2 Developer Portal application
2. **Get the API endpoint** from the WSO2 Developer Portal
3. **Add the chat completions URL** to `.env` following the `{PROVIDER_NAME}_CHAT_COMPLETIONS_URL` pattern
4. **Add a new entry** under `providers:` in `config.yaml` with `MODEL` and `ENABLED` fields
5. No code changes are needed: the app automatically detects the defined providers

Example for adding a new "CLAUDE" provider:
- Subscribe to Claude API in WSO2 Developer Portal
- Add `CLAUDE_CHAT_COMPLETIONS_URL=https://your-wso2-server:8243/claudeapi/v1/messages` to `.env`
- Add the following to `config.yaml`:
  ```yaml
  CLAUDE:
    MODEL: "claude-3-sonnet"
    ENABLED: true
  ```

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