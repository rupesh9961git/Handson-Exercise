import os
import dotenv
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
dotenv.load_dotenv()

key = os.getenv("OLLAMA_API_KEY")
url = os.getenv("OLLAMA_BASE_URL")
model_name = os.getenv("OLLAMA_MODEL_NAME")

model = ChatOllama(
            model=model_name,
            base_url=url,
            headers={
                "Authorization": f"Bearer {key}"
            },
            max_tokens=100,
            temperature=1,
            max_retries=3,
            timeout=120
)

_sap_base_url = os.getenv("SAP_HYPERSPACE_BASE_URL", "http://localhost:6655")
_sap_api_key  = os.getenv("SAP_HYPERSPACE_API_KEY")
_sap_model    = os.getenv("SAP_HYPERSPACE_MODEL", "claude-sonnet-latest")

model_sap = ChatAnthropic(
    model=_sap_model,
    api_key=_sap_api_key,
    base_url=f"{_sap_base_url.rstrip('/')}/anthropic",
    max_tokens=1500,
    timeout=120,
)