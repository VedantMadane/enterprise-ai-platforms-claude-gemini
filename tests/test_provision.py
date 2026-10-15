import json
import pytest
from pathlib import Path
from meridian.config import BASE_DIR, ENVIRONMENTS_DIR
from meridian.provision.render import render_all, render_environment

def test_provisioning_all_environments(tmp_path):
    out_dir = tmp_path / "provision_output"
    manifests = render_all(env_dir=ENVIRONMENTS_DIR, out_dir=out_dir)

    assert len(manifests) == 3
    envs = {m["environment"] for m in manifests}
    assert envs == {"dev", "staging", "prod"}

    for env in ["dev", "staging", "prod"]:
        env_folder = out_dir / env
        assert (env_folder / "permissions.json").exists()
        assert (env_folder / "claude_desktop_config.json").exists()
        assert (env_folder / "claude_plugin_manifest.json").exists()
        assert (env_folder / "gemini_extension.json").exists()

        # Check permissions content
        with open(env_folder / "permissions.json", "r", encoding="utf-8") as f:
            perm = json.load(f)
            assert perm["environment"] == env
            assert "usage:read" in perm["scopes"]
            assert "capabilities:write" in perm["scopes"]
