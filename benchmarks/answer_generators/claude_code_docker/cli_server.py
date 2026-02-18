import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import litellm

litellm.set_verbose = True

app = FastAPI()

class CompletionRequest(BaseModel):
    model: str
    messages: list
    response_schema: dict | None = Field(default=None, alias='response_schema')
    api_key: str | None = Field(default=None, alias='api_key')

@app.post("/completion")
async def completion(request: CompletionRequest):
    try:
        kwargs = {
            "model": request.model,
            "messages": request.messages,
        }
        if request.api_key:
            kwargs["api_key"] = request.api_key
        
        if request.response_schema:
            kwargs["response_model"] = {
                "name": "structured_output",
                "description": "Structured output based on schema",
                "parameters": request.response_schema,
            }
            
        response = await litellm.acompletion(**kwargs)
        
        return JSONResponse(content=response.model_dump())

    except Exception as e:
        return JSONResponse(content={"error": str(e), "error_type": type(e).__name__}, status_code=500)

@app.get("/")
async def health_check():
    return {"status": "ok"}
