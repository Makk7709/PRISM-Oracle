from datetime import datetime
import json
import os
from python.helpers import files


def _load_version_file():
    """Load version info from VERSION.json (baked at build/deploy time)."""
    for candidate in [
        os.path.join(files.get_base_dir(), "VERSION.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "VERSION.json"),
    ]:
        if os.path.isfile(candidate):
            try:
                with open(candidate) as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def get_git_info():
    # Try live git repo first
    try:
        from git import Repo
        repo_path = files.get_base_dir()
        repo = Repo(repo_path)

        if repo.bare:
            raise ValueError("bare repo")

        branch = repo.active_branch.name if repo.head.is_detached is False else ""
        commit_hash = repo.head.commit.hexsha
        commit_time = datetime.fromtimestamp(repo.head.commit.committed_date).strftime('%y-%m-%d %H:%M')

        short_tag = ""
        try:
            tag = repo.git.describe(tags=True)
            tag_split = tag.split('-')
            if len(tag_split) >= 3:
                short_tag = "-".join(tag_split[:-1])
            else:
                short_tag = tag
        except Exception:
            tag = ""

        version = branch[0].upper() + " " + (short_tag or commit_hash[:7]) if branch else (short_tag or commit_hash[:7])

        return {
            "branch": branch,
            "commit_hash": commit_hash,
            "commit_time": commit_time,
            "tag": tag,
            "short_tag": short_tag,
            "version": version,
        }
    except Exception:
        pass

    # Fallback: VERSION.json (for Docker deployments without .git)
    vf = _load_version_file()
    if vf:
        return {
            "branch": vf.get("branch", ""),
            "commit_hash": vf.get("commit_hash", ""),
            "commit_time": vf.get("commit_time", ""),
            "tag": vf.get("tag", ""),
            "short_tag": vf.get("short_tag", ""),
            "version": vf.get("version", vf.get("short_tag", "unknown")),
        }

    return {
        "branch": "",
        "commit_hash": "",
        "commit_time": "",
        "tag": "",
        "short_tag": "",
        "version": "unknown",
    }


def get_version():
    try:
        git_info = get_git_info()
        return str(git_info.get("short_tag", "")).strip() or git_info.get("version", "unknown")
    except Exception:
        return "unknown"