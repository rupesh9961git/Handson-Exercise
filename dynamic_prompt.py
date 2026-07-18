from langchain.agents.middleware import dynamic_prompt, ModelRequest

def dynamic_prompt_middleware(request: ModelRequest) -> ModelRequest:
    request.override()