import argparse
import asyncio
import os
import sys

from meridian.mcp.server import MeridianMCPServer

def main():
    parser = argparse.ArgumentParser(description="Meridian MCP Usage & Capability Connector")
    parser.add_argument("--user", "-u", default=None, help="Simulated actor email or user_id")
    parser.add_argument("--env", "-e", default=None, help="Environment name: dev, staging, prod")
    args = parser.parse_args()

    user_ident = args.user or os.environ.get("MERIDIAN_ACTOR_EMAIL") or os.environ.get("MERIDIAN_ACTOR_ID")
    env_name = args.env or os.environ.get("MERIDIAN_ENV", "prod")

    server = MeridianMCPServer(user_identifier=user_ident, env_name=env_name)
    asyncio.run(server.run_stdio())

if __name__ == "__main__":
    main()
