"""
Conversational AI agent. Uses Claude with tool-use to answer questions
about the portfolio company's financials, run scenarios, and search
for market data. NEVER makes up numbers — always calls a real tool.
"""

import os
from dotenv import load_dotenv

from chat.tools import TOOL_DEFINITIONS, execute_tool
from value_creation.context import build_context_block

load_dotenv()


def build_system_prompt(company_name: str, sector: str, context_block: str) -> str:
    return f"""You are a PE operating partner's AI analyst for {company_name}, a {sector} company.

You have access to complete financial data, analysis, and modeling tools for this company.

RULES — FOLLOW THESE STRICTLY:
1. NEVER make up numbers. ALWAYS call a tool to get real data before citing any metric.
2. When asked "what if" questions, ALWAYS use the run_scenario tool. Never estimate in your head.
3. If you need information you don't have, ASK the user. Don't guess.
4. Be direct and specific. Reference actual numbers from tool results.
5. When recommending actions, size the EBITDA impact in dollars.
6. Use search_market for any external information (competitors, AI tools, industry data).

WHAT YOU KNOW (from the loaded financial data):
{context_block}

You remember everything discussed in this conversation. Be concise but thorough."""


def chat(
    user_message: str,
    conversation_history: list[dict],
    context: dict,
) -> tuple[str, list[dict]]:
    """
    Process a user message and return the AI response + updated history.

    context dict contains: analysis, ingested, assumptions, model, research,
    company_name, sector.

    Returns (response_text, updated_conversation_history).
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return "Claude API not available.", conversation_history

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        return "API key not set.", conversation_history

    # Build context block
    analysis = context.get("analysis")
    research = context.get("research")
    company = context.get("company_name", "")
    sector = context.get("sector", "")

    ctx_block = build_context_block(analysis, research, company, sector)
    system = build_system_prompt(company, sector, ctx_block)

    # Add user message
    conversation_history.append({"role": "user", "content": user_message})

    client = Anthropic()

    # Agent loop — keeps running while Claude wants to use tools
    messages = list(conversation_history)
    max_iterations = 5  # Safety limit

    for _ in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process tool calls
            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input, context)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Add to messages for next iteration
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Claude is done — extract text response
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            # Update conversation history with the final exchange
            conversation_history.append({"role": "assistant", "content": text})

            return text, conversation_history

    return "I'm having trouble processing this. Could you rephrase?", conversation_history
