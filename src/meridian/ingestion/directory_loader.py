import json
from pathlib import Path
from typing import Dict, List, Optional
from meridian.config import DATA_DIR
from meridian.models.directory import User, Group

class Directory:
    def __init__(
        self,
        users: List[User],
        groups: List[Group],
    ):
        self.users = users
        self.groups = groups
        
        self.users_by_id: Dict[str, User] = {u.user_id: u for u in users}
        self.users_by_email: Dict[str, User] = {u.email.lower(): u for u in users}
        
        self.groups_by_id: Dict[str, Group] = {g.group_id: g for g in groups}
        self.groups_by_claude_rbac: Dict[str, Group] = {g.claude_rbac_group_id: g for g in groups}
        self.groups_by_gcp_project: Dict[str, Group] = {g.gcp_project_id: g for g in groups}

    def get_user(self, identifier: str) -> Optional[User]:
        if not identifier:
            return None
        clean = identifier.strip()
        # Try direct ID
        if clean in self.users_by_id:
            return self.users_by_id[clean]
        # Try email
        clean_email = clean.lower()
        if clean_email in self.users_by_email:
            return self.users_by_email[clean_email]
        # In case identifier has user: prefix (e.g. gcp_principal)
        if clean_email.startswith("user:"):
            email_part = clean_email.split("user:", 1)[1]
            if email_part in self.users_by_email:
                return self.users_by_email[email_part]
        return None

    def get_group(self, group_id: str) -> Optional[Group]:
        return self.groups_by_id.get(group_id)

    def get_group_for_claude_rbac(self, rbac_id: str) -> Optional[Group]:
        return self.groups_by_claude_rbac.get(rbac_id)

    def get_group_for_gcp_project(self, project_id: str) -> Optional[Group]:
        return self.groups_by_gcp_project.get(project_id)

def load_directory(data_dir: Path = DATA_DIR) -> Directory:
    users_path = data_dir / "directory" / "users.json"
    groups_path = data_dir / "directory" / "groups.json"
    
    with open(users_path, "r", encoding="utf-8") as f:
        users_raw = json.load(f)["users"]
    users = [User(**u) for u in users_raw]

    with open(groups_path, "r", encoding="utf-8") as f:
        groups_raw = json.load(f)["groups"]
    groups = [Group(**g) for g in groups_raw]

    return Directory(users=users, groups=groups)
