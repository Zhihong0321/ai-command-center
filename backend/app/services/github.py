from datetime import datetime
from sqlalchemy.orm import Session
from app import models
from app.config import settings
import re


def _extract_github_owner_repo(github_url: str):
    """Extract owner/repo from a GitHub URL."""
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", github_url)
    if not match:
        raise ValueError(f"Cannot parse GitHub URL: {github_url}")
    return match.group(1), match.group(2)


def sync_github_repo(repo_id: str, db: Session) -> dict:
    repo = db.query(models.Repo).filter(models.Repo.id == repo_id).first()
    if not repo:
        return {"error": "Repo not found"}

    # Use token from settings if available, else fallback to env
    github_token = settings.GITHUB_TOKEN
    db_setting = db.query(models.Setting).filter(models.Setting.key == "github_token").first()
    if db_setting and db_setting.value:
        github_token = db_setting.value

    if not github_token:
        return {"error": "GITHUB_TOKEN not configured. Skipping GitHub sync."}

    try:
        from github import Github, GithubException
        g = Github(github_token)
        owner, repo_name = _extract_github_owner_repo(repo.github_url)
        gh_repo = g.get_repo(f"{owner}/{repo_name}")
    except Exception as e:
        return {"error": f"GitHub connection failed: {str(e)}"}

    commits_added = 0
    prs_synced = 0

    # ── Sync Commits ────────────────────────────────────────────────────────
    try:
        existing_shas = {
            r[0]
            for r in db.query(models.GithubCommit.sha)
            .filter(models.GithubCommit.repo_id == repo.id)
            .all()
        }
        for commit in gh_repo.get_commits()[:30]:  # last 30 commits
            if commit.sha not in existing_shas:
                gc = models.GithubCommit(
                    repo_id=repo.id,
                    sha=commit.sha,
                    author=commit.commit.author.name if commit.commit.author else "unknown",
                    message=commit.commit.message[:500],
                    url=commit.html_url,
                    committed_at=commit.commit.author.date if commit.commit.author else None,
                )
                db.add(gc)
                commits_added += 1
    except Exception as e:
        return {"error": f"Commit sync failed: {str(e)}"}

    # ── Sync PRs ────────────────────────────────────────────────────────────
    try:
        for pr in gh_repo.get_pulls(state="all", sort="updated", direction="desc")[:20]:
            existing = (
                db.query(models.GithubPR)
                .filter(
                    models.GithubPR.repo_id == repo.id,
                    models.GithubPR.pr_number == pr.number,
                )
                .first()
            )
            status = "merged" if pr.merged else ("closed" if pr.state == "closed" else "open")
            if existing:
                existing.title = pr.title[:500]
                existing.status = status
                existing.updated_at = pr.updated_at
                existing.synced_at = datetime.utcnow()
            else:
                gpr = models.GithubPR(
                    repo_id=repo.id,
                    pr_number=pr.number,
                    title=pr.title[:500],
                    status=status,
                    url=pr.html_url,
                    author=pr.user.login if pr.user else "unknown",
                    updated_at=pr.updated_at,
                )
                db.add(gpr)
                prs_synced += 1
    except Exception as e:
        db.commit()
        return {"error": f"PR sync failed: {str(e)}", "commits_added": commits_added}

    db.commit()
    # Stamp repo freshness
    repo.last_synced_at = datetime.utcnow()
    if commits_added > 0:
        latest = (
            db.query(models.GithubCommit)
            .filter(models.GithubCommit.repo_id == repo.id)
            .order_by(models.GithubCommit.committed_at.desc())
            .first()
        )
        if latest and latest.committed_at:
            repo.last_commit_date = latest.committed_at
    db.commit()
    return {
        "ok": True,
        "commits_added": commits_added,
        "prs_synced": prs_synced,
        "synced_at": datetime.utcnow().isoformat(),
    }
