from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from chart_agent import generate_chart
import json
import uvicorn

app = FastAPI()

class ChartRequest(BaseModel):
    text: str

@app.post("/generate_chart")
async def create_chart(request: ChartRequest):
    try:
        result = generate_chart(request.text)
        return json.loads(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 