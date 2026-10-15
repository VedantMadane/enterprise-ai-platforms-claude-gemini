import json
from pathlib import Path
from typing import Dict, Any, List
import yaml
import jsonschema

from meridian.config import BASE_DIR, ENVIRONMENTS_DIR, CONTRACTS_DIR
from meridian.ingestion.directory_loader import load_directory

OUTPUT_DIR = BASE_DIR / "dist" / "provision"

# Schema to validate rendered environment permissions
PERMISSIONS_MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["environment", "server_name", "scopes", "capability_defaults", "groups"],
    "properties": {
        "environment": {"type": "string", "enum": ["dev", "staging", "prod"]},
        "server_name": {"type": "string"},
        "scopes": {
            "type": "object",
            "required": ["usage:read", "capabilities:write"],
            "properties": {
                "usage:read": {
                    "type": "object",
                    "required": ["roles", "group_visibility"],
                    "properties": {
                        "roles": {"type": "array", "items": {"type": "string"}},
                        "group_visibility": {"type": "string", "enum": ["all", "own_group"]}
                    }
                },
                "capabilities:write": {
                    "type": "object",
                    "required": ["roles"],
                    "properties": {
                        "roles": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        },
        "capability_defaults": {"type": "object"},
        "groups": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

CLAUDE_CONFIG_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2026-12/schema",
    "type": "object",
    "required": ["mcpServers"],
    "properties": {
        "mcpServers": {
            "type": "object"
        }
    }
}

def render_environment(env_file: Path, out_dir: Path) -> Dict[str, Any]:
    with open(env_file, "r", encoding="utf-8") as f:
        env_raw = yaml.safe_load(f)

    env_name = env_raw.get("environment")
    host_info = env_raw.get("host", {})
    server_name = host_info.get("server_name", f"meridian-usage-{env_name}")
    directory = load_directory()
    group_ids = [g.group_id for g in directory.groups]

    # 1. Render permissions manifest
    permissions_manifest = {
        "environment": env_name,
        "server_name": server_name,
        "scopes": env_raw.get("scopes", {}),
        "capability_defaults": env_raw.get("capability_defaults", {}),
        "groups": group_ids,
        "active_roles": {
            "member": [u.email for u in directory.users if u.role == "member"],
            "team_lead": [u.email for u in directory.users if u.role == "team_lead"],
            "platform_admin": [u.email for u in directory.users if u.role == "platform_admin"],
        }
    }

    # Validate against JSON schema
    jsonschema.validate(instance=permissions_manifest, schema=PERMISSIONS_MANIFEST_SCHEMA)

    env_out = out_dir / env_name
    env_out.mkdir(parents=True, exist_ok=True)

    with open(env_out / "permissions.json", "w", encoding="utf-8") as f:
        json.dump(permissions_manifest, f, indent=2)

    # 2. Render Claude Desktop host configuration
    claude_config = {
        "mcpServers": {
            server_name: {
                "command": "python",
                "args": ["-m", "meridian.mcp.runner", "--env", env_name],
                "env": {
                    "MERIDIAN_ENV": env_name,
                    "PYTHONPATH": "src"
                }
            }
        }
    }
    jsonschema.validate(instance=claude_config, schema=CLAUDE_CONFIG_SCHEMA)

    with open(env_out / "claude_desktop_config.json", "w", encoding="utf-8") as f:
        json.dump(claude_config, f, indent=2)

    # 3. Render Claude Plugin manifest
    claude_plugin_manifest = {
        "schema_version": "v1",
        "name_for_model": f"meridian_usage_{env_name}",
        "name_for_human": f"Meridian Usage & Governance ({env_name.upper()})",
        "description_for_model": "Connector for querying enterprise AI token usage, costs, and group capability controls.",
        "description_for_human": "Track Claude & Gemini usage across teams and inspect capability governance.",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "mcp",
            "server_name": server_name
        },
        "tools": [
            "usage_summary",
            "top_users",
            "capability_status",
            "set_capability"
        ]
    }
    with open(env_out / "claude_plugin_manifest.json", "w", encoding="utf-8") as f:
        json.dump(claude_plugin_manifest, f, indent=2)

    # 4. Render Gemini CLI extension configuration
    gemini_cli_ext = {
        "extension_id": f"meridian.usage.{env_name}",
        "version": "1.0.0",
        "name": f"Meridian Usage Platform ({env_name})",
        "description": "Vertex AI and Claude usage analytics and capability management",
        "entrypoint": {
            "type": "mcp",
            "command": "python",
            "args": ["-m", "meridian.mcp.runner", "--env", env_name]
        },
        "environments": {
            "MERIDIAN_ENV": env_name
        },
        "supported_tools": [
            "usage_summary",
            "top_users",
            "capability_status",
            "set_capability"
        ]
    }
    with open(env_out / "gemini_extension.json", "w", encoding="utf-8") as f:
        json.dump(gemini_cli_ext, f, indent=2)

    return permissions_manifest

def render_all(env_dir: Path = ENVIRONMENTS_DIR, out_dir: Path = OUTPUT_DIR) -> List[Dict[str, Any]]:
    results = []
    out_dir.mkdir(parents=True, exist_ok=True)
    env_files = sorted(list(env_dir.glob("*.yaml")))
    for env_path in env_files:
        manifest = render_environment(env_path, out_dir)
        results.append(manifest)
    return results

def main():
    print(f"Provisioning environments from {ENVIRONMENTS_DIR} into {OUTPUT_DIR}...")
    manifests = render_all()
    print(f"Successfully rendered and validated {len(manifests)} environments:")
    for m in manifests:
        print(f"  - [{m['environment']}] Server: {m['server_name']}, Read: {m['scopes']['usage:read']['roles']}, Write: {m['scopes']['capabilities:write']['roles']}")

if __name__ == "__main__":
    main()
