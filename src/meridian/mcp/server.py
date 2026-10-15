import asyncio
import os
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel
from mcp.server.mcpserver import MCPServer

from meridian.config import CURRENT_ENV, DATA_DIR, SQLITE_PATH
from meridian.auth.rbac import RBACPolicy
from meridian.ingestion.directory_loader import Directory, load_directory
from meridian.models.directory import User
from meridian.models.capabilities import Capability, Denial
from meridian.store.periods import parse_period
from meridian.store.sqlite_store import SQLiteStore

class MeridianMCPServer:
    def __init__(
        self,
        user_identifier: Optional[str] = None,
        env_name: str = CURRENT_ENV,
        store: Optional[SQLiteStore] = None,
        directory: Optional[Directory] = None,
    ):
        self.env_name = env_name
        self.directory = directory or load_directory(DATA_DIR)
        self.store = store or SQLiteStore(SQLITE_PATH)
        self.rbac = RBACPolicy(env_name)

        # Resolve active user identity
        ident = (
            user_identifier
            or os.environ.get("MERIDIAN_ACTOR_EMAIL")
            or os.environ.get("MERIDIAN_ACTOR_ID")
            or "priya.nair@meridianls.example"
        )
        self.current_user: Optional[User] = self.directory.get_user(ident)
        if not self.current_user:
            raise ValueError(f"Actor '{ident}' not found in directory.")

        # Ensure seed capabilities exist
        group_ids = [g.group_id for g in self.directory.groups]
        self.store.seed_capabilities_from_env(self.env_name, group_ids)

        # Initialize underlying MCP server
        self.mcp = MCPServer(name=f"meridian-usage-{self.env_name}")
        self._register_tools()

    def usage_summary(self, period: str, group: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns AI usage and cost by platform and totals for a period and group.
        """
        allowed, resolved_group, denial = self.rbac.check_usage_read(
            self.current_user, group, store=self.store
        )
        if not allowed or denial:
            return denial.model_dump()

        try:
            window = parse_period(period)
        except ValueError as e:
            return Denial(
                error="permission_denied",
                reason=f"Invalid period parameter: {str(e)}",
                required_scope="usage:read"
            ).model_dump()

        summary = self.store.get_usage_summary(resolved_group, window)
        return summary.model_dump()

    def top_users(self, period: str, group: Optional[str] = None, limit: int = 10) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Returns top users ranked by total token usage for a given period.
        """
        allowed, resolved_group, denial = self.rbac.check_usage_read(
            self.current_user, group, store=self.store
        )
        if not allowed or denial:
            return denial.model_dump()

        try:
            window = parse_period(period)
        except ValueError as e:
            return Denial(
                error="permission_denied",
                reason=f"Invalid period parameter: {str(e)}",
                required_scope="usage:read"
            ).model_dump()

        limit = max(1, min(25, limit))
        users = self.store.get_top_users(resolved_group, window, limit=limit)
        return [u.model_dump() for u in users]

    def capability_status(self, group: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Returns current capability status for the specified group or caller's group.
        """
        # Capability status requires usage:read scope
        read_scope = self.rbac.config.get("scopes", {}).get("usage:read", {})
        allowed_roles = read_scope.get("roles", [])
        if self.current_user.role not in allowed_roles:
            return Denial(
                error="permission_denied",
                reason=f"Role '{self.current_user.role}' is not granted scope 'usage:read' in '{self.env_name}'.",
                required_scope="usage:read"
            ).model_dump()

        caller_group = self.current_user.primary_group
        resolved_group = group or caller_group

        visibility = read_scope.get("group_visibility", "own_group")
        if visibility == "own_group" and self.current_user.role != "platform_admin":
            if group and group != caller_group:
                return Denial(
                    error="permission_denied",
                    reason=f"User '{self.current_user.name}' ({self.current_user.role}) cannot inspect capabilities for group '{group}'.",
                    required_scope="usage:read"
                ).model_dump()
            resolved_group = caller_group

        caps = self.store.get_capabilities(resolved_group)
        return [c.model_dump() for c in caps]

    def set_capability(self, group: str, capability: str, enabled: bool) -> Dict[str, Any]:
        """
        Enables or disables a capability for a group. Requires capabilities:write scope.
        """
        allowed, denial = self.rbac.check_capabilities_write(self.current_user, group)
        if not allowed or denial:
            return denial.model_dump()

        # Validate capability enum
        try:
            cap_enum = Capability(capability)
        except ValueError:
            return Denial(
                error="permission_denied",
                reason=f"Unknown capability '{capability}'. Valid: usage-connector, web-search, code-execution",
                required_scope="capabilities:write"
            ).model_dump()

        updated = self.store.set_capability(
            group_id=group,
            capability=cap_enum.value,
            enabled=enabled,
            actor=self.current_user.email
        )
        return updated.model_dump()

    def _register_tools(self):
        @self.mcp.tool(
            name="usage_summary",
            description="Query AI token usage and costs across Claude and Gemini for a period and group."
        )
        def tool_usage_summary(period: str, group: Optional[str] = None) -> Dict[str, Any]:
            return self.usage_summary(period=period, group=group)

        @self.mcp.tool(
            name="top_users",
            description="Get the top users ranked by token consumption for a given period."
        )
        def tool_top_users(period: str, group: Optional[str] = None, limit: int = 10) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
            return self.top_users(period=period, group=group, limit=limit)

        @self.mcp.tool(
            name="capability_status",
            description="Inspect the enable/disable status of platform capabilities for a group."
        )
        def tool_capability_status(group: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
            return self.capability_status(group=group)

        @self.mcp.tool(
            name="set_capability",
            description="Enable or disable a capability for a group (requires capabilities:write scope)."
        )
        def tool_set_capability(group: str, capability: str, enabled: bool) -> Dict[str, Any]:
            return self.set_capability(group=group, capability=capability, enabled=enabled)

    async def run_stdio(self):
        await self.mcp.run_stdio_async()
