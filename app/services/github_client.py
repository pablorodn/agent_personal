from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def list_repos(self, per_page: int = 30) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{GITHUB_API_BASE}/user/repos", headers=self._headers, params={"per_page": per_page})
            response.raise_for_status()
            return response.json()

    async def list_issues(self, owner: str, repo: str, state: str = "open") -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues", headers=self._headers, params={"state": state})
            response.raise_for_status()
            return response.json()

    async def create_issue(self, owner: str, repo: str, title: str, body: str | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues", headers=self._headers, json={"title": title, "body": body})
            response.raise_for_status()
            return response.json()

    async def create_repo(self, name: str, private: bool = True) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{GITHUB_API_BASE}/user/repos", headers=self._headers, json={"name": name, "private": private})
            response.raise_for_status()
            return response.json()
