from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain.agents import create_agent
from agent import get_user_info, User
from model import model, model_sap
from agent_with_store import agent as store_agent, store, NAMESPACE
from mcp_client import client as mcp_client
import json
import logging
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
from langgraph.checkpoint.memory import InMemorySaver

logger = logging.getLogger("server")

agent1 = create_agent(model=model, tools=[get_user_info], context_schema=User)
agent_sap = None  # initialized in lifespan after event loop is running


@asynccontextmanager
async def lifespan(_: FastAPI):
    global agent_sap
    try:
        mcp_tools = await mcp_client.get_tools()
        logger.info("MCP tools loaded: %s", [t.name for t in mcp_tools])
    except Exception as e:
        logger.warning("MCP tools unavailable (%s), starting without them.", e)
        mcp_tools = []
    agent_sap = create_agent(
        model=model_sap,
        tools=[get_user_info, *mcp_tools],
        context_schema=User,
        middleware=[HumanInTheLoopMiddleware(
            interrupt_on={t.name: True for t in mcp_tools},
            description_prefix="Tool execution pending approval. Please review the tool's input and output before proceeding.",
        )],
        checkpointer=InMemorySaver()
    )
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str
    user_id: str = "RK01"


class ChatResponse(BaseModel):
    message: str


@app.post("/askMeTest", response_model=ChatResponse)
async def ask_me_test(req: ChatRequest):
    response = agent1.invoke(
        {"messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": req.message},
        ]},
        context=User(user_id=req.user_id),
    )
    last = response["messages"][-1]
    return ChatResponse(message=last.content)


class ApprovalRequest(BaseModel):
    user_id: str = "RK01"
    decisions: list[dict]  # e.g. [{"type": "approve"}] or [{"type": "reject", "message": "..."}]


@app.post("/sapAgent", response_model=ChatResponse)
async def sap_agent(req: ChatRequest):
    logger.info("[Anthropic/SAP] user_id=%s message=%r", req.user_id, req.message)
    config = {"configurable": {"thread_id": req.user_id}}

    # Only add system message on fresh threads — checkpointer replays history on existing ones
    state = await agent_sap.aget_state(config)
    has_history = bool(state.values.get("messages"))
    messages = [] if has_history else [{"role": "system", "content": "You are a helpful assistant."}]
    messages.append({"role": "user", "content": req.message})

    try:
        response = await agent_sap.ainvoke(
            {"messages": messages},
            config=config,
            context=User(user_id=req.user_id),
        )
        # Check if graph paused for human approval
        state = await agent_sap.aget_state(config)
        pending = [i.value for t in (state.tasks or []) for i in (t.interrupts or [])]
        if pending:
            return ChatResponse(message=json.dumps({
                "type": "interrupt",
                "interrupts": [pending],
            }))
        last = response["messages"][-1]
        return ChatResponse(message=extract_content(last))
    except GraphInterrupt as exc:
        interrupts = [i.value for i in exc.args[0]] if exc.args else []
        return ChatResponse(message=json.dumps({
            "type": "interrupt",
            "interrupts": [interrupts],
        }))


@app.post("/sapAgent/resume", response_model=ChatResponse)
async def sap_agent_resume(req: ApprovalRequest):
    logger.info("[Anthropic/SAP resume] user_id=%s decisions=%s", req.user_id, req.decisions)
    config = {"configurable": {"thread_id": req.user_id}}
    response = await agent_sap.ainvoke(
        Command(resume={"decisions": req.decisions}),
        config=config,
    )
    last = response["messages"][-1]
    return ChatResponse(message=extract_content(last))


def build_store_context(message: str) -> str:
    items = store.search(NAMESPACE, query=message)
    if not items:
        return ""
    entries = "\n\n".join(f"[{item.key}]:\n{item.value['content']}" for item in items)
    return f"\n\nRelevant stored knowledge (use this to answer questions):\n{entries}"


def extract_content(msg) -> str:
    content = msg.content if hasattr(msg, "content") else ""
    if isinstance(content, list):
        return " ".join(
            c.get("text", "") if isinstance(c, dict) else str(c)
            for c in content
        )
    return content


@app.post("/askMe")
async def ask_me(req: ChatRequest):
    logger.info("[Ollama] user_id=%s message=%r", req.user_id, req.message)
    store_context = build_store_context(req.message)
    input_data = {
        "messages": [
            {"role": "system", "content": (
                "You are a helpful assistant. Answer questions using the stored knowledge below "
                "when relevant, including when the user refers to a subject using pronouns like "
                "'he', 'she', 'they', or 'it'."
                + store_context
            )},
            {"role": "user", "content": req.message},
        ]
    }

    async def event_stream():
        for chunk in store_agent.stream(
            input_data,
            context=User(user_id=req.user_id),
            stream_mode=["custom", "messages"],
        ):
            mode, data = chunk
            if mode == "custom":
                yield json.dumps({"type": "progress", "content": str(data)}) + "\n"
            elif mode == "messages":
                content = extract_content(data[0])
                if content:
                    yield json.dumps({"type": "message", "content": content}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
