import sys
import os
import uuid
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Ensure local imports work correctly 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import Agent

app = FastAPI()
hr_agent = Agent()

@app.post("/")
async def handle_request(request: Request):
    try:
        data = await request.json()
        
        # Validate JSON-RPC A2A format 
        if data.get("jsonrpc") != "2.0" or data.get("method") != "message/send":
            return JSONResponse(status_code=400, content={"error": "Invalid request format."})
        
        # Extract user message from the A2A payload 
        req_id = data.get("id", str(uuid.uuid4()))
        params = data.get("params", {})
        message = params.get("message", {})
        parts = message.get("parts", [])
        
        user_text = ""
        for part in parts:
            if part.get("kind") == "text":
                user_text += part.get("text", "")
                
        # Process the message with our Agent
        agent_response = hr_agent.process_message(user_text)
        
        # Build A2A compliant response 
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "id": str(uuid.uuid4()),
                "kind": "task",
                "status": {
                    "state": "completed",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "artifacts": [
                    {
                        "id": str(uuid.uuid4()),
                        "kind": "text",
                        "parts": [
                            {
                                "kind": "text",
                                "text": agent_response
                            }
                        ]
                    }
                ]
            }
        }
        return JSONResponse(content=response)
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import click
    
    @click.command()
    @click.option("--host", default="0.0.0.0", help="Host to bind to")
    @click.option("--port", default=5000, help="Port to bind to")
    def run(host, port):
        uvicorn.run(app, host=host, port=port)
        
    run()