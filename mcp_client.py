import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
# from mcp.client.sse import sse_client


class MCPClient:

    def __init__(self):

        self.url = "http://127.0.0.1:9000/mcp"


    async def call_tool(self, tool_name, **kwargs):

        async with streamablehttp_client(self.url) as streams:
            read_stream, write_stream, *_ = streams
            async with ClientSession(read_stream, write_stream) as session:

                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    kwargs
                )

                return result.content


client = MCPClient()


def invoke_tool(tool_name, **kwargs):

    return asyncio.run(
        client.call_tool(
            tool_name,
            **kwargs
        )
    )