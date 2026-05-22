import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GitHub PR Validator")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _check_status(label: str, value: bool) -> str:
    icon = "✅" if value else "❌"
    return f"{icon} {label}"


@mcp.tool()
def list_open_prs(owner: str, repo: str) -> str:
    """Lista todos os Pull Requests abertos de um repositório."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls?state=open&per_page=50"
    resp = httpx.get(url, headers=_headers())
    resp.raise_for_status()
    prs = resp.json()

    if not prs:
        return f"Nenhum PR aberto em {owner}/{repo}."

    lines = [f"## PRs abertos em {owner}/{repo} ({len(prs)} total)\n"]
    for pr in prs:
        reviewers = [r["login"] for r in pr.get("requested_reviewers", [])]
        reviewer_info = ", ".join(reviewers) if reviewers else "nenhum"
        lines.append(f"- **#{pr['number']}** {pr['title']} — reviewers: {reviewer_info}")

    return "\n".join(lines)


@mcp.tool()
def validate_pr(owner: str, repo: str, pr_number: int) -> str:
    """Valida um PR específico: verifica reviewers atribuídos e status dos checks de CI/CD."""
    # Fetch PR details
    pr_resp = httpx.get(f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}", headers=_headers())
    pr_resp.raise_for_status()
    pr = pr_resp.json()

    # Fetch CI checks via commit SHA
    sha = pr["head"]["sha"]
    checks_resp = httpx.get(
        f"{BASE_URL}/repos/{owner}/{repo}/commits/{sha}/check-runs",
        headers=_headers(),
    )
    checks_resp.raise_for_status()
    check_runs = checks_resp.json().get("check_runs", [])

    # --- Reviewers ---
    reviewers = [r["login"] for r in pr.get("requested_reviewers", [])]
    reviews_resp = httpx.get(
        f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews", headers=_headers()
    )
    reviews_resp.raise_for_status()
    completed_reviews = reviews_resp.json()
    approved_by = [r["user"]["login"] for r in completed_reviews if r["state"] == "APPROVED"]

    has_reviewers = bool(reviewers or approved_by)

    # --- CI checks ---
    if check_runs:
        failed = [c for c in check_runs if c["conclusion"] in ("failure", "timed_out", "cancelled")]
        pending = [c for c in check_runs if c["status"] in ("in_progress", "queued")]
        ci_ok = not failed and not pending
        ci_summary_parts = []
        if failed:
            ci_summary_parts.append(f"{len(failed)} falhando")
        if pending:
            ci_summary_parts.append(f"{len(pending)} em andamento")
        if ci_ok:
            ci_summary_parts.append(f"todos os {len(check_runs)} checks passaram")
        ci_detail = ", ".join(ci_summary_parts)
    else:
        ci_ok = None  # sem checks configurados
        ci_detail = "nenhum check configurado"

    # --- Build report ---
    lines = [
        f"## Validação do PR #{pr_number}: {pr['title']}",
        f"**Autor:** {pr['user']['login']}",
        f"**Branch:** `{pr['head']['ref']}` → `{pr['base']['ref']}`",
        f"**URL:** {pr['html_url']}",
        "",
        "### Checklist",
        _check_status(
            f"Reviewers atribuídos ({', '.join(reviewers) if reviewers else 'nenhum pendente'})",
            has_reviewers,
        ),
    ]

    if approved_by:
        lines.append(f"   ↳ Aprovado por: {', '.join(approved_by)}")

    if ci_ok is None:
        lines.append(f"⚠️  CI/CD: {ci_detail}")
    else:
        lines.append(_check_status(f"CI/CD ({ci_detail})", ci_ok))

    if check_runs:
        lines.append("\n### Checks de CI/CD")
        for c in check_runs:
            status = c["conclusion"] or c["status"]
            icon = "✅" if c["conclusion"] == "success" else ("⏳" if c["status"] != "completed" else "❌")
            lines.append(f"{icon} `{c['name']}` — {status}")

    all_ok = has_reviewers and (ci_ok is True or ci_ok is None)
    lines.append(f"\n**Resultado geral:** {'✅ PR válido' if all_ok else '❌ PR precisa de atenção'}")

    return "\n".join(lines)


@mcp.tool()
def validate_all_prs(owner: str, repo: str) -> str:
    """Valida todos os PRs abertos de um repositório e retorna um resumo consolidado."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls?state=open&per_page=50"
    resp = httpx.get(url, headers=_headers())
    resp.raise_for_status()
    prs = resp.json()

    if not prs:
        return f"Nenhum PR aberto em {owner}/{repo}."

    results = [f"# Relatório de Validação — {owner}/{repo}\n"]
    ok_count = 0
    attention_count = 0

    for pr in prs:
        report = validate_pr(owner, repo, pr["number"])
        results.append(report)
        results.append("\n---\n")
        if "✅ PR válido" in report:
            ok_count += 1
        else:
            attention_count += 1

    results.append(
        f"## Resumo: {ok_count} válido(s) ✅ | {attention_count} precisam de atenção ❌"
    )
    return "\n".join(results)


if __name__ == "__main__":
    mcp.run()
