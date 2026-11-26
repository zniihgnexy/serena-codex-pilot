import asyncio
import json
from pathlib import Path
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from pilot import SERENA, SERENA_ARGS, WORK, prepare


async def main():
    with tempfile.TemporaryDirectory(prefix="serena-check-", dir=WORK) as folder:
        checkout = Path(folder) / "checkout"
        prepare(checkout, regression=False)
        server = StdioServerParameters(
            command=str(SERENA), args=SERENA_ARGS, cwd=str(checkout),
            env={"SERENA_HOME": str(Path(folder) / "serena-home"), "UV_OFFLINE": "1"},
        )
        with (WORK / "serena-check.log").open("w", encoding="utf-8") as log:
            async with stdio_client(server, errlog=log) as (reader, writer):
                async with ClientSession(reader, writer) as client:
                    await client.initialize()
                    result = await client.call_tool("find_symbol", {
                        "name_path_pattern": "Dataset/_getitem",
                        "relative_path": "src/datasets/arrow_dataset.py",
                    })
                    reply = result.model_dump(mode="json", by_alias=True)
                    if result.is_error or "Dataset/_getitem" not in json.dumps(reply):
                        raise RuntimeError(f"Serena symbol lookup failed. See .work/serena-check.log.\n{reply}")
    print("PASS: Serena found Dataset/_getitem through MCP and Pyright.")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=120))
