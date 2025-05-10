# Salesforce Permission Assistant Backend

This is the backend service for the Salesforce Permission Assistant LWC component. It provides an API for checking field permissions, querying Salesforce data, and creating data visualizations.

## Features

- **Permission Queries**: Check if a user/profile has access to specific fields or objects
- **Data Queries**: Answer natural language questions about Salesforce data
- **Data Visualization**: Generate Chart.js compatible visualizations
- **Multi-Agent AI**: Uses CrewAI with Google Gemini to process requests with specialized agents

## Project Structure

- `app.py` - FastAPI entry point that handles API requests
- `agent.py` - CrewAI agent implementation that processes queries
- `tools.py` - Custom tools for the agents to interact with Salesforce data
- `requirements.txt` - Python dependencies

## Setup Instructions

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server locally:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

3. The API will be available at http://localhost:8000

### Deployment to Render.com

1. Create a new Web Service on Render.com
2. Connect your GitHub repository
3. Configure the following settings:
   - **Name**: `salesforce-ai-assistant` (or your preferred name)
   - **Runtime**: Python 3.9+
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**: None needed (API key is hardcoded)

## API Endpoints

### POST /process_query

Processes a natural language query about Salesforce data or permissions.

**Request Body:**
```json
{
  "query_text": "Does the Sales Rep profile have access to the Account.Rating field?",
  "user_id": "005XXXXXXXXXXXXXXX",
  "username": "user@example.com",
  "context": {
    "profile": "Sales Rep",
    "objectPermissions": { ... },
    "fieldPermissions": { ... }
  }
}
```

**Response:**
```json
{
  "text": "The field Account.Rating is not visible to the current user's profile Sales Rep.",
  "field_access": true,
  "query_text": "Does the Sales Rep profile have access to the Account.Rating field?"
}
```

### GET /available_models

Returns information about available language models.

**Response:**
```json
{
  "models": ["gemini-1.5-flash"]
}
```

### GET /ping

Simple ping endpoint for connectivity tests.

**Response:**
```json
{
  "ping": "pong",
  "status": "ok",
  "model": "gemini-1.5-flash"
}
```

## Implementation Notes

- This backend uses Google's Gemini 1.5 Flash model instead of OpenAI GPT
- The Gemini API key is hardcoded in the `agent.py` file (not recommended for production)
- The multi-agent system uses specialized agents for different tasks:
  - Query Analyzer: Understands natural language queries
  - Data Expert: Generates SOQL queries and interprets results
  - Security Expert: Checks field/object permissions
  - Visualization Expert: Creates data visualizations
  - Response Formatter: Creates clean, readable responses

## Security Considerations

- In a production environment, store your API key in an environment variable
- Consider implementing additional authentication for the API
- Add rate limiting to prevent abuse
- Set specific CORS origins instead of allowing all origins 