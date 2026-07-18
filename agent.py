from langchain.agents import create_agent
from model import model
from langchain.tools import tool, ToolRuntime
from pydantic import BaseModel as PydanticBase
import platform
import sys

@tool("get_runtime_details",
    description="Get the runtime details of the agent.",
    return_direct=True,
)
def get_runtime_details(runtime:ToolRuntime):
    """
    Get the runtime details of the agent."""
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "current_working_directory": sys.path,
        "runtime": runtime.config,
        "version": runtime.context,
        "executable": runtime.execution_info,
        "stack_trace": runtime.state,
        "error_message": runtime.server_info,
        "timestamp": runtime.store,
        "tools": runtime.tools,
        "agent": runtime.stream_writer,
        "model": runtime.tool_call_id
    }

USER_DATABASE = {
    "user1": {"user_id": "user1", "name": "Alice", "age": 30, "city": "New York", "email": "alice@example.com", "phone": "123-456-7890"},
    "user2": {"user_id": "user2", "name": "Bob", "age": 25, "city": "Los Angeles", "email": "bob@example.com", "phone": "987-654-3210"},
    "user3": {"user_id": "user3", "name": "Charlie", "age": 35, "city": "Chicago", "email": "charlie@example.com", "phone": "555-555-5555"},
    "RK01": {"user_id": "RK01", "name": "Rupesh Kumar", "age": 30, "city": "Bangalore", "email": "rupesh.kumar@example.com", "phone": "111-222-3333"}
}

class User(PydanticBase):
    user_id: str
    name: str = ""
    age: int = 0
    city: str = ""
    email: str = ""
    phone: str = ""

@tool("get_user_info",
    description="Get user information from the database.",
    return_direct=True
)
def get_user_info(runtime: ToolRuntime[User]) -> User:
    """
    Get user information from the database.
    """
    user_id = runtime.context.user_id
    user_data = USER_DATABASE.get(user_id)
    if user_data:
        return User(
            user_id=user_data["user_id"],
            name=user_data["name"],
            age=user_data["age"],
            city=user_data["city"],
            email=user_data["email"],
            phone=user_data["phone"],
        )
    else:
        raise ValueError(f"User with ID {user_id} not found.")

tools = [get_user_info]
agent = create_agent(model=model, tools=tools, context_schema=User)

response = agent.invoke({"messages": [{"role": "user", "content": "Tell me about me"},
                                      {"role": "system", "content": "You are a helpful assistant."}]},
                        context=User(user_id="user2"))

tool_message = response["messages"][-1]
print(tool_message.content)
@tool("get_user_info",
    description="Get user information from the database.",
    return_direct=True
)
def get_user_info(runtime: ToolRuntime[User]) -> User:
    """
    Get user information from the database.
    """
    user_id = runtime.context.user_id
    user_data = USER_DATABASE.get(user_id)
    if user_data:
        return User(
            user_id=user_data["user_id"],
            name=user_data["name"],
            age=user_data["age"],
            city=user_data["city"],
            email=user_data["email"],
            phone=user_data["phone"],
        )
    else:
        raise ValueError(f"User with ID {user_id} not found.")

tools = [get_user_info]
agent = create_agent(model=model, tools=tools, context_schema=User)

response = agent.invoke({"messages": [{"role": "user", "content": "Tell me about me"},
                                      {"role": "system", "content": "You are a helpful assistant."}]},
                        context=User(user_id="user2"))

tool_message = response["messages"][-1]
print(tool_message.content)