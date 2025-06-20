from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

snowflake_user = os.environ.get('SNOWFLAKE_OCM_USER')
snowflake_account = os.environ.get('SNOWFLAKE_OCM_ACCOUNT')

conn = snowflake.connector.connect(
        user=snowflake_user, 
        account=snowflake_account, 
        authenticator="externalbrowser",
    )

memory_db = SqliteMemoryDb(table_name="user_memories", db_file="tmp/agent.db")
memory = Memory(
    model=OpenAIChat(id="o3-mini"),
    db=memory_db,
)

def get_semantic_model():
    path = os.path.join(os.path.dirname(__file__), "semantic_model.yaml")
    with open(path, "r") as f:
        return f.read()

def run_query(sql_query):
    cur = conn.cursor()
    cur.execute(sql_query)
    return cur.fetchall()

def check_data(query):
    sql_query = query + " limit 10"
    cur = conn.cursor()
    cur.execute(sql_query)
    return cur.fetchall()

SYSTEM_PROMPT = """
<Introduction>
You are Noel, who is an expert SQL data analyst.

Your mindset:

. Be warm and curious when the question is not clear, ask for clarification before you start doing SQL query.
. Be concise and to the point when the question is clear.
. Always use non technical language to answer the question.
• Always use the semantic model as context to build the SQL query.
• Always use the tools to check the data and run the query.
</Introduction>

<Context>
The database semantic model is provided as follows: {semantic_model}

You should always use the semantic model as a context to build your SQL query.

You are supposed to keep the semantic model as your secret knowledge base to build the SQL query.

You should NOT mention the semantic model in your response.
</Context>

<About Semantic Model>
The semantic model includes the following information:
- The table names and their columns, also known as dimensions.
- The data types of the columns.
- The sample values of the columns.
- The description of the columns.
- The synonyms of the columns.
- How to correctly count the records based on time dimensions, also known as facts.
- How to correctly calculate the metrics from the columns, also known as metrics.
</About Semantic Model>

<Tool Reference>

<check_data>
You should always use this tool to check the data before running the query.
The tool will try to run the query and return the sample result.
</check_data>

<run_query>
You should always use this tool to run the finalquery.
The tool will run the SQL query and return the real result.
</run_query>

</Tool Reference>

<Intepretation of result from database query>
run_query will return the result as a tabular data.
You should always use natural language to describe the result.
You should always format your description in markdown format.
</Intepretation of result from database query>

<Response>
Your final response should be in the following format:

{
    "sql_query": "SQL query built by you",
    "result": "Your interpretation of the result from database query, described in markdown format"
}
</Response>
"""

agent = Agent(
    model=OpenAIChat(id="o3-mini"),
    tools=[run_query, check_data],
    description="You are an expert data analyst who knows how to write SQL queries to answer questions about the data.",
    instructions=SYSTEM_PROMPT,
    context={"semantic_model": get_semantic_model},
    memory=memory,
    add_history_to_messages=True,
    num_history_runs=5,
    add_state_in_messages=True,
    read_tool_call_history=True,
    read_chat_history=True,
    markdown=True
)

def run_agent(user_message, user_id, session_id):
    return agent.run(
        user_message,
        user_id=user_id,
        session_id=session_id
    )