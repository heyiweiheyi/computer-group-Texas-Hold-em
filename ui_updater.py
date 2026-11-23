"""Background GitHub update checker and one-click updater (supports both Git and ZIP installs)."""

import io
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zipfile


REPO_OWNER = "heyiweiheyi"
REPO_NAME = "computer-group-Texas-Hold-em"
REPO_BRANCH = "main"

COMMITS_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{REPO_BRANCH}"
RAW_VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}/VERSION"
ARCHIVE_ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{REPO_BRANCH}.zip"

LOCAL_COMMIT_FILE = ".local_commit"
VERSION_FILE = "VERSION"
USER_AGENT = "TexasHoldemUpdater/1.0"


def _subprocess_kwargs():
    kwargs = {}
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def get_local_commit_sha(app_dir):
    """Return the local 40-char commit SHA from git or .local_commit, or None."""
    git_dir = os.path.join(app_dir, ".git")
    if os.path.exists(git_dir):
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=4,
                **_subprocess_kwargs(),
            )
            if proc.returncode == 0:
                sha = proc.stdout.strip()
                if len(sha) >= 7:
                    return sha
        except (OSError, subprocess.SubprocessError):
            pass

    marker = os.path.join(app_dir, LOCAL_COMMIT_FILE)
    if os.path.isfile(marker):
        try:
            with open(marker, "r", encoding="utf-8") as fh:
                sha = fh.read().strip()
                if len(sha) >= 7:
                    return sha
        except OSError:
            pass
    return None


def get_local_version(app_dir):
    """Read local VERSION file if present."""
    path = os.path.join(app_dir, VERSION_FILE)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            pass
    return ""


def _save_local_commit(app_dir, sha):
    if not sha or os.path.exists(os.path.join(app_dir, ".git")):
        return
    try:
        with open(os.path.join(app_dir, LOCAL_COMMIT_FILE), "w", encoding="utf-8") as fh:
            fh.write(sha.strip() + "\n")
    except OSError:
        pass


def fetch_remote_latest(timeout=8):
    """Fetch the latest commit metadata from GitHub."""
    req = urllib.request.Request(
        COMMITS_API_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    sha = data.get("sha", "").strip()
    commit = data.get("commit", {})
    raw_msg = commit.get("message", "")
    first_line = raw_msg.splitlines()[0].strip() if raw_msg else ""
    date_str = commit.get("committer", {}).get("date", "")
    return {
        "sha": sha,
        "short_sha": sha[:7],
        "message": first_line,
        "date": date_str,
    }


def fetch_remote_version(timeout=6):
    """Fetch the VERSION file from GitHub main branch."""
    req = urllib.request.Request(RAW_VERSION_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8").strip()
    except (OSError, urllib.error.URLError):
        return ""


def check_for_updates(app_dir, timeout=8):
    """Compare local installation against GitHub main and return status dict."""
    try:
        remote = fetch_remote_latest(timeout=timeout)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {
            "ok": False,
            "has_update": False,
            "error": f"Could not reach GitHub: {exc}",
        }

    remote_sha = remote["sha"]
    local_sha = get_local_commit_sha(app_dir)

    if local_sha:
        has_update = local_sha != remote_sha
    else:
        local_ver = get_local_version(app_dir)
        remote_ver = fetch_remote_version(timeout=min(timeout, 6))
        if local_ver and remote_ver and local_ver == remote_ver:
            _save_local_commit(app_dir, remote_sha)
            local_sha = remote_sha
            has_update = False
        else:
            has_update = True

    return {
        "ok": True,
        "has_update": has_update,
        "local_sha": local_sha or "",
        "remote_sha": remote_sha,
        "short_sha": remote["short_sha"],
        "message": remote["message"],
        "date": remote["date"],
    }


def apply_zip_update(app_dir, zip_bytes, target_sha=""):
    """Extract a GitHub branch archive safely into app_dir."""
    app_abs = os.path.abspath(app_dir)
    req_path = os.path.join(app_abs, "requirements.txt")
    old_req = ""
    if os.path.isfile(req_path):
        try:
            with open(req_path, "r", encoding="utf-8") as fh:
                old_req = fh.read()
        except OSError:
            pass

    updated_files = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = info.filename.replace("\\", "/").split("/")
            if len(parts) <= 1:
                continue
            rel_parts = parts[1:]
            if not rel_parts or any(p in ("", ".", "..") for p in rel_parts):
                continue
            if rel_parts[0] in (".git", "__pycache__") or rel_parts[-1] == LOCAL_COMMIT_FILE:
                continue

            dest = os.path.abspath(os.path.join(app_abs, *rel_parts))
            if not (dest == app_abs or dest.startswith(app_abs + os.sep)):
                continue

            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(info, "r") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            updated_files += 1

    new_req = ""
    if os.path.isfile(req_path):
        try:
            with open(req_path, "r", encoding="utf-8") as fh:
                new_req = fh.read()
        except OSError:
            pass

    if target_sha:
        _save_local_commit(app_abs, target_sha)

    return {
        "updated_files": updated_files,
        "requirements_changed": new_req.strip() != old_req.strip(),
    }


def _install_requirements_if_needed(app_dir):
    req_path = os.path.join(app_dir, "requirements.txt")
    if not os.path.isfile(req_path):
        return True
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=90,
            **_subprocess_kwargs(),
        )
        if proc.returncode == 0:
            return True
        proc2 = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-i",
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                "-r",
                req_path,
            ],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=90,
            **_subprocess_kwargs(),
        )
        return proc2.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def apply_update(app_dir, remote_sha="", timeout=25):
    """Pull updates via git pull (for git repos) or GitHub ZIP download (for ZIP installs)."""
    git_dir = os.path.join(app_dir, ".git")
    if os.path.exists(git_dir):
        try:
            proc = subprocess.run(
                ["git", "pull", "--ff-only", "origin", REPO_BRANCH],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                **_subprocess_kwargs(),
            )
            if proc.returncode == 0:
                return {
                    "ok": True,
                    "method": "git",
                    "message": "Updated via git pull! Click Restart Now to apply.",
                }
            stderr = (proc.stderr or proc.stdout or "").strip()
            return {
                "ok": False,
                "error": f"git pull failed: {stderr.splitlines()[0] if stderr else 'unknown error'}",
            }
        except FileNotFoundError:
            pass  # Fall through to ZIP download if git binary is missing
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "error": f"git pull error: {exc}"}

    try:
        req = urllib.request.Request(ARCHIVE_ZIP_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            zip_bytes = resp.read()

        if not remote_sha:
            try:
                remote_sha = fetch_remote_latest(timeout=6)["sha"]
            except Exception:
                remote_sha = ""

        result = apply_zip_update(app_dir, zip_bytes, target_sha=remote_sha)
        if result["requirements_changed"]:
            _install_requirements_if_needed(app_dir)

        return {
            "ok": True,
            "method": "zip",
            "message": f"Updated {result['updated_files']} files! Click Restart Now to apply.",
        }
    except (OSError, urllib.error.URLError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": f"Download/update failed: {exc}"}


class UpdateController:
    """Thread-safe controller bridging background update tasks with the Pygame UI."""

    def __init__(self, app_dir):
        self.app_dir = app_dir
        self._lock = threading.Lock()
        self._state = {
            "status": "idle",
            "has_update": False,
            "local_sha": get_local_commit_sha(app_dir) or "",
            "remote_sha": "",
            "short_sha": "",
            "commit_message": "",
            "detail": "Click 'Check Again' to check GitHub for updates.",
            "restart_required": False,
        }

    def snapshot(self):
        with self._lock:
            return dict(self._state)

    def _set(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)

    def check_async(self):
        with self._lock:
            if self._state["status"] in ("checking", "updating"):
                return
            self._state["status"] = "checking"
            self._state["detail"] = "Checking GitHub for latest commits..."

        def _worker():
            res = check_for_updates(self.app_dir)
            if not res["ok"]:
                self._set(
                    status="error",
                    detail=res["error"],
                )
            elif res["has_update"]:
                self._set(
                    status="update_available",
                    has_update=True,
                    local_sha=res["local_sha"],
                    remote_sha=res["remote_sha"],
                    short_sha=res["short_sha"],
                    commit_message=res["message"],
                    detail=f"New version ({res['short_sha']}): {res['message']}",
                )
            else:
                self._set(
                    status="up_to_date",
                    has_update=False,
                    local_sha=res["local_sha"],
                    remote_sha=res["remote_sha"],
                    short_sha=res["short_sha"],
                    commit_message=res["message"],
                    detail=f"Already up to date ({res['short_sha']}).",
                )

        threading.Thread(target=_worker, daemon=True).start()

    def update_async(self):
        with self._lock:
            if self._state["status"] in ("checking", "updating"):
                return
            remote_sha = self._state.get("remote_sha", "")
            self._state["status"] = "updating"
            self._state["detail"] = "Downloading & applying update from GitHub..."

        def _worker():
            res = apply_update(self.app_dir, remote_sha=remote_sha)
            if res["ok"]:
                new_sha = get_local_commit_sha(self.app_dir) or remote_sha
                self._set(
                    status="updated",
                    has_update=False,
                    local_sha=new_sha,
                    restart_required=True,
                    detail=res["message"],
                )
            else:
                self._set(
                    status="error",
                    detail=res["error"],
                )

        threading.Thread(target=_worker, daemon=True).start()
