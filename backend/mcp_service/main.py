import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str

# Configuration for the Creatomate MCP Server
# We assume the user has 'npm' and the package installed globally or via npx
server_params = StdioServerParameters(
    command=os.getenv("MCP_SERVER_COMMAND", "npx.cmd"), # Windows compatibility
    args=os.getenv("MCP_SERVER_ARGS", "-y @creatomate/mcp-server").split(" "),
    env={**os.environ} 
)

@app.post("/generate")
async def generate_video(request: GenerateRequest):
    try:
        # Establish MCP Connection
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                await session.initialize()

                # Execute the video generation tool
                result = await session.call_tool(
                    "render_video",
                    arguments={"prompt": request.prompt}
                )

                # Inspect result content
                # This depends on exactly what the MCP server returns.
                # Usually it's a list with TextContent
                if not result.content:
                     raise HTTPException(status_code=500, detail="Empty response from MCP server")

                output = result.content[0].text
                return {"status": "success", "result": output}

    except Exception as e:
        print(f"MCP Error: {e}")
        # In production, log full traceback
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use port 8001 to avoid conflict with potential other services
    uvicorn.run(app, host="0.0.0.0", port=8001)
