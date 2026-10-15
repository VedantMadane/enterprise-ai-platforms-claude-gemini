import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from meridian.config import ENVIRONMENTS_DIR, CURRENT_ENV
from meridian.models.capabilities import Denial
from meridian.models.directory import User
from meridian.store.sqlite_store import SQLiteStore

class RBACPolicy:
    def __init__(self, env_name: str = CURRENT_ENV):
        self.env_name = env_name
        self.config = self._load_env_config(env_name)

    def _load_env_config(self, env_name: str) -> Dict[str, Any]:
        env_file = ENVIRONMENTS_DIR / f"{env_name}.yaml"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        # Fallback to dev defaults
        return {
            "environment": env_name,
            "scopes": {
                "usage:read": {
                    "roles": ["member", "team_lead", "platform_admin"],
                    "group_visibility": "all"
                },
                "capabilities:write": {
                    "roles": ["team_lead", "platform_admin"]
                }
            }
        }

    def check_usage_read(
        self,
        caller: User,
        target_group: Optional[str],
        store: Optional[SQLiteStore] = None
    ) -> Tuple[bool, Optional[str], Optional[Denial]]:
        """
        Validates whether the caller may read usage data.
        Returns:
            (allowed: bool, resolved_group: Optional[str], denial: Optional[Denial])
        """
        read_scope = self.config.get("scopes", {}).get("usage:read", {})
        allowed_roles = read_scope.get("roles", [])
        visibility = read_scope.get("group_visibility", "own_group")

        # 1. Role scope check
        if caller.role not in allowed_roles:
            return False, None, Denial(
                error="permission_denied",
                reason=f"Role '{caller.role}' is not granted scope 'usage:read' in environment '{self.env_name}'.",
                required_scope="usage:read"
            )

        caller_group = caller.primary_group
        resolved_group = target_group or caller_group

        # 2. Group visibility check
        if visibility == "own_group" and caller.role != "platform_admin":
            # Target must match caller's own group
            if target_group and target_group != caller_group:
                return False, None, Denial(
                    error="permission_denied",
                    reason=f"User '{caller.name}' ({caller.role}) is restricted to own group '{caller_group}' and cannot view group '{target_group}'.",
                    required_scope="usage:read"
                )
            resolved_group = caller_group

        # 3. Check if usage-connector capability is enabled for target group
        if store and resolved_group:
            is_enabled = store.is_capability_enabled(resolved_group, "usage-connector")
            if not is_enabled:
                return False, None, Denial(
                    error="permission_denied",
                    reason=f"Capability 'usage-connector' is disabled for group '{resolved_group}' in environment '{self.env_name}'.",
                    required_scope="usage:read"
                )

        return True, resolved_group, None

    def check_capabilities_write(
        self,
        caller: User,
        target_group: str
    ) -> Tuple[bool, Optional[Denial]]:
        """
        Validates whether the caller may change capability controls for target_group.
        """
        write_scope = self.config.get("scopes", {}).get("capabilities:write", {})
        allowed_roles = write_scope.get("roles", [])

        if caller.role not in allowed_roles:
            return False, Denial(
                error="permission_denied",
                reason=f"Role '{caller.role}' is not granted scope 'capabilities:write' in environment '{self.env_name}'.",
                required_scope="capabilities:write"
            )

        # In staging/dev where team leads have write access, ensure they can only write their own group if team_lead
        if caller.role == "team_lead" and caller.primary_group != target_group:
            return False, Denial(
                error="permission_denied",
                reason=f"Team lead '{caller.name}' can only modify capabilities for their own group '{caller.primary_group}', not '{target_group}'.",
                required_scope="capabilities:write"
            )

        return True, None
