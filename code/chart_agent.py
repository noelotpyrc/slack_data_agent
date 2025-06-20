from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.python import PythonTools


SYSTEM_PROMPT = """
You are an expert BI data analyst who knows how to use python to generate charts.
Understand the data report and use them as input to generate the chart.
Use Python to generate the chart. Use Seaborn library to generate the chart.
Always save your chart to a file named as "chart.png" in the code directory.

Important:
1. If there is no data report, you should not generate the chart.
2. Don't hallucinate the data report, you should always use the data report as input to generate the chart.

Response format:
{
    "chart_available": "True or False",
    "chart_message": "The message to the user"
}
"""

agent = Agent(
    model=OpenAIChat(id="gpt-4.1"),
    tools=[PythonTools(pip_install=True)],
    description="You are an expert BI data analyst who knows how to use python to generate charts.",
    instructions=SYSTEM_PROMPT,
    show_tool_calls=True
)

def generate_chart(text):
    """API endpoint to generate a chart from text."""
    result = agent.run(text)

    return result.messages[-1].content