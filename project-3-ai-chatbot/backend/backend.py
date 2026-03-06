import asyncio
from typing import AsyncGenerator
import config

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from langgraph.prebuilt import create_react_agent
system_prompt = "Act as a AI chatbot who is smart and friendly"
from langchain_core.messages.ai import AIMessage

def test_agent(llm_id, query, allow_search, system_prompt, provider):
    """
    AI agent with timeout, retry, and max tokens enforcement
    """
    # Normalize provider name
    provider_type = provider.lower().strip()
    
    # Create LLM with max_tokens from config
    llm_kwargs = {
        "model": llm_id,
        "max_tokens": config.AI_MAX_TOKENS,
        "timeout": config.AI_TIMEOUT
    }
    
    if "groq" in provider_type:
        llm = ChatGroq(**llm_kwargs)
    elif "openai" in provider_type:
        llm = ChatOpenAI(**llm_kwargs)
    else:
        raise ValueError(f"Invalid provider: '{provider}'. Must be 'groq' or 'openai'.")

    tools = [TavilySearchResults(max_results=5)] if allow_search else []

    # Direct LLM call (fast) when no tools needed
    if not allow_search:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [SystemMessage(content=system_prompt)]
        for q in query:
            messages.append(HumanMessage(content=q))
        response = llm.invoke(messages)
        return response.content

    # Only use agent (slower) when search tools are needed
    agent = create_react_agent(model=llm, tools=tools, prompt=system_prompt)
    state = {"messages": query}
    
    # Retry logic with exponential backoff
    for attempt in range(config.AI_MAX_RETRIES):
        try:
            response = agent.invoke(state)
            messages = response.get("messages")
            ai_messages = [msg.content for msg in messages if isinstance(msg, AIMessage)]
            return ai_messages[-1]
            
        except asyncio.TimeoutError:
            return "⏱️ Request timed out. The AI took too long to respond. Please try again with a simpler question."
            
        except Exception as e:
            error_message = str(e)
            
            # Retry on rate limits
            if "429" in error_message and attempt < config.AI_MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                asyncio.sleep(wait_time)
                continue
            
            # Handle specific errors
            if "insufficient_quota" in error_message or "429" in error_message:
                return "❌ OpenAI API Error: You've exceeded your quota. Please check your billing at https://platform.openai.com/account/billing or use 'groq' provider instead."
            elif "401" in error_message or "invalid_api_key" in error_message:
                return "❌ API Error: Invalid API key. Please check your .env file."
            else:
                return f"❌ Error: {error_message}"
    
    return "❌ Request failed after multiple retries. Please try again later."


async def stream_agent_response(llm_id, query, allow_search, system_prompt, provider) -> AsyncGenerator[str, None]:
    """
    Streaming version of AI agent - yields chunks as they arrive
    """
    provider_type = provider.lower().strip()
    
    llm_kwargs = {
        "model": llm_id,
        "max_tokens": config.AI_MAX_TOKENS,
        "timeout": config.AI_TIMEOUT,
        "streaming": True
    }
    
    if "groq" in provider_type:
        llm = ChatGroq(**llm_kwargs)
    elif "openai" in provider_type:
        llm = ChatOpenAI(**llm_kwargs)
    else:
        yield f"data: {{\"error\": \"Invalid provider: {provider}\"}}\n\n"
        return

    enhanced_prompt = f"""{system_prompt}

IMPORTANT INSTRUCTIONS:
- Provide detailed, comprehensive answers with explanations
- Include relevant examples and context when appropriate
"""

    tools = [TavilySearchResults(max_results=5)] if allow_search else []
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=enhanced_prompt
    )

    state = {"messages": query}
    
    try:
        async for chunk in agent.astream(state):
            # Extract AI message chunks
            if "messages" in chunk:
                for msg in chunk["messages"]:
                    if isinstance(msg, AIMessage) and msg.content:
                        yield f"data: {msg.content}\n\n"
    except Exception as e:
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
