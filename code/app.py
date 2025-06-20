import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from agent import run_agent
import json
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# For testing purposes
#TEST_MODE = True  # Set to False in production
#PLACEHOLDER_IMAGE = os.path.join(os.path.dirname(__file__), "placeholder.png")
#logger.debug(f"Placeholder image path: {PLACEHOLDER_IMAGE}")
#logger.debug(f"Placeholder image exists: {os.path.exists(PLACEHOLDER_IMAGE)}")

CHART_PATH = os.path.join(os.path.dirname(__file__), "chart.png")
CHART_SERVICE_URL = "http://localhost:8000/generate_chart"

def call_chart_service(text):
    """Call the chart generation service API."""
    try:
        response = requests.post(CHART_SERVICE_URL, json={"text": text})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling chart service: {e}")
        return None

@app.event("message")
def handle_mention(event, say, client):
    """Handle direct mentions of the bot."""
    # Remove the bot mention from the text
    text = event['text']
    user_id = event['user']
    channel = event['channel']
    session_id = channel
    
    # Extract the actual query by removing the bot mention
    # The format is usually <@BOTID> actual message
    query = ' '.join(text.split()[1:])
    
    logger.debug(f"Received mention from user {user_id} in channel {channel}")
    logger.debug(f"Query after removing mention: {query}")

    try:
        # Send initial "thinking" message
        thinking_msg = say("🤔 I'm analyzing your query and preparing the SQL... Please wait a moment.")
        
        # Run the SQL agent
        agent_response = run_agent(query, user_id, session_id)
        json_str = None
        
        try:
            json_str = agent_response.messages[-1].content
            logger.debug(f"Extracted JSON string: {json_str[:200]}...")
        except (AttributeError, IndexError) as e:
            logger.error(f"Failed to extract content from agent response: {e}")
            client.chat_update(
                channel=channel,
                ts=thinking_msg['ts'],
                text="❌ Sorry, I couldn't process your query. There was an error in the response format."
            )
            return
            
        try:
            parsed = json.loads(json_str)
            sql_query = parsed.get('sql_query')
            result = parsed.get('result')
            
            logger.debug(f"Parsed response - SQL Query: {bool(sql_query)}, Result: {bool(result)}")
            
            if sql_query and result:
                # Update thinking message to show success
                client.chat_update(
                    channel=channel,
                    ts=thinking_msg['ts'],
                    text="✅ Analysis complete! Here are your results:"
                )
                
                # Show the formatted results
                formatted_message = (
                    f"*SQL Query:*\n"
                    f"```sql\n{sql_query}\n```\n"
                    f"*Result:*\n"
                    f"{result}"
                )
                say(formatted_message)
                
                # Send a "working on it" message for chart generation
                working_msg = say("🎨 I'm generating a visual chart for this data... Please wait a moment.")
                
                # Try to generate a chart from the result using the API
                logger.debug("Calling chart generation service")
                chart_data = call_chart_service(result)
                
                if chart_data and chart_data.get('chart_available') == "True" and os.path.exists(CHART_PATH):
                    logger.debug(f"Chart generated successfully at {CHART_PATH}")
                    try:
                        # Upload the chart
                        client.files_upload_v2(
                            channel=channel,
                            file=CHART_PATH,
                            initial_comment="✨ Here's your data visualization:"
                        )
                        logger.debug("Chart uploaded successfully")
                        
                        # Update the "working on it" message to indicate completion
                        client.chat_update(
                            channel=channel,
                            ts=working_msg['ts'],
                            text="✅ Chart generation complete! Check out the visualization above."
                        )
                    except Exception as e:
                        logger.error(f"Error uploading chart: {e}", exc_info=True)
                        # Update the "working on it" message to indicate error
                        client.chat_update(
                            channel=channel,
                            ts=working_msg['ts'],
                            text="❌ Sorry, I couldn't upload the chart. Please try again."
                        )
                elif chart_data:
                    logger.debug(f"No chart generated: {chart_data.get('chart_message')}")
                    # Update the "working on it" message when no chart could be generated
                    client.chat_update(
                        channel=channel,
                        ts=working_msg['ts'],
                        text="ℹ️ I couldn't create a meaningful chart for this data. The data might not be suitable for visualization."
                    )
                else:
                    logger.error("Chart service unavailable")
                    # Update the "working on it" message when service is unavailable
                    client.chat_update(
                        channel=channel,
                        ts=working_msg['ts'],
                        text="🔧 Sorry, the chart generation service is currently unavailable. Please try again later."
                    )
            elif result:
                # Update thinking message for result-only response
                client.chat_update(
                    channel=channel,
                    ts=thinking_msg['ts'],
                    text="✅ Analysis complete! Here's what I found:"
                )
                say(result)
            else:
                logger.warning("No result found in response")
                client.chat_update(
                    channel=channel,
                    ts=thinking_msg['ts'],
                    text="❌ Sorry, I couldn't find any results in the response. Please try rephrasing your query."
                )
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            client.chat_update(
                channel=channel,
                ts=thinking_msg['ts'],
                text="❌ Sorry, I received an invalid response format. Please try again."
            )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        # If thinking_msg was successfully sent, update it
        try:
            client.chat_update(
                channel=channel,
                ts=thinking_msg['ts'],
                text=f"❌ Sorry, something went wrong while processing your request. Error: {str(e)}"
            )
        except:
            # If thinking_msg wasn't sent or can't be updated, send a new message
            say(f"❌ Sorry, there was an error processing your request: {str(e)}")

# Start your app
if __name__ == "__main__":
    logger.info("Starting Slack bot...")
    # Check permissions before starting
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()