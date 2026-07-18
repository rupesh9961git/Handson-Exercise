from langchain.tools import tool, ToolRuntime
from langgraph.store.memory import InMemoryStore
from model import model
from langchain.agents import create_agent
from agent import User

NAMESPACE = ("responses",)
store = InMemoryStore()

@tool
def get_store_info(query: str, runtime: ToolRuntime) -> str:
    """
    Search the store for information relevant to the query.
    Always call this before answering any question — it may contain
    previously stored facts (e.g. details about a person or topic).
    Returns all stored entries so you can find the relevant one.
    """
    writer = runtime.stream_writer
    writer(f"Searching store for: {query}")
    store = runtime.store
    items = store.search(NAMESPACE, query=query)
    if not items:
        writer("No stored information found.")
        return "No stored information found."
    results = []
    for item in items:
        writer(f"Found stored entry: [{item.key}]")
        results.append(f"[{item.key}]: {item.value['content']}")
    return "Stored knowledge:\n" + "\n\n".join(results)


@tool
def set_store_info(key: str, content: str, runtime: ToolRuntime) -> str:
    """
    Store information under a descriptive key so it can be retrieved later.
    Use a short, meaningful key (e.g. 'PM of India', 'user preference').
    """
    writer = runtime.stream_writer
    writer(f"Saving '{key}' to store...")
    store = runtime.store
    store.put(NAMESPACE, key, {"content": content})
    writer(f"'{key}' saved successfully.")
    return f"Stored successfully under key '{key}'."


agent = create_agent(
    model=model,
    tools=[get_store_info, set_store_info],
    store=store,
    context_schema=User,
)
