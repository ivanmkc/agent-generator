"""Cli Server module."""

import asyncio
import os
import json
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()


@app.post("/")
async def run_command(request: Request):
    try:
        # FastAPI handles JSON automatically, but for raw flexibility we can read body
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Expecting 'args' list: ["gemini", "prompt", ...]
        args = data.get("args", [])

        # Optional: 'env' dictionary to merge with system env
        request_env = data.get("env", {})

        if not args or args[0] != "gemini":
            raise HTTPException(
                status_code=400, detail="Invalid command. Must start with 'gemini'."
            )

        print(f"Executing: {args}")

        # Merge env
        full_env = os.environ.copy()
        full_env.update(request_env)

        # Run the command asynchronously
        # This is the non-blocking magic
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )

        stdout, stderr = await proc.communicate()

        response = {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": proc.returncode,
        }

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        return PlainTextResponse(str(e), status_code=500)


@app.post("/read_file")
async def read_file(request: Request):
    try:
        data = await request.json()
        path = data.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Missing path")

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        # Basic security: ensure we don't escape too far if needed?
        # For this dev tool, we assume trusted access.

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return JSONResponse(content={"content": content})
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reading file: {e}")
        return PlainTextResponse(str(e), status_code=500)


@app.get("/version")
async def get_version():
    try:
        if os.path.exists("version.txt"):
            with open("version.txt", "r") as f:
                return f.read().strip()
        return "unknown"
    except Exception:
        return "unknown"


@app.get("/")
async def health_check():
    return PlainTextResponse("Gemini CLI Server Ready")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    print(f"Starting FastAPI server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
