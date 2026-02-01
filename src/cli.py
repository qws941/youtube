"""YouTube Automation CLI - Typer 기반."""
from __future__ import annotations

import asyncio
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import logging
import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

from config import get_settings
from src.core.orchestrator import Orchestrator, get_orchestrator, JobStatus

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.CRITICAL if os.getenv("QUIET") else logging.INFO
    ),
)

app = typer.Typer(
    name="ytauto",
    help="YouTube Automation System - Faceless 채널 자동화",
    no_args_is_help=True,
)
schedule_app = typer.Typer(help="스케줄러 관리")
config_app = typer.Typer(help="설정 관리")
youtube_app = typer.Typer(help="YouTube 인증 관리")
app.add_typer(schedule_app, name="schedule")
app.add_typer(config_app, name="config")
app.add_typer(youtube_app, name="youtube")

console = Console()


class ChannelChoice(str, Enum):
    horror = "horror"
    facts = "facts"
    finance = "finance"
    all = "all"


def _get_dry_run() -> bool:
    return os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")


@app.command()
def run(
    channel: ChannelChoice = typer.Option(..., "--channel", "-c", help="채널 선택"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="시뮬레이션 모드"),
):
    """단일 영상 또는 전체 채널 실행."""
    dry_run = dry_run or _get_dry_run()
    orchestrator = get_orchestrator(dry_run=dry_run)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        if channel == ChannelChoice.all:
            task = progress.add_task("[cyan]전체 채널 실행 중...", total=3)
            job_ids = asyncio.run(_run_all(orchestrator, progress, task))
            console.print(f"\n[green]✓[/green] 완료: {len(job_ids)}개 작업")
        else:
            task = progress.add_task(f"[cyan]{channel.value} 채널 실행 중...", total=1)
            job_id = asyncio.run(_run_single(orchestrator, channel.value))
            progress.update(task, advance=1)
            console.print(f"\n[green]✓[/green] 작업 완료: {job_id}")

    _show_job_summary(orchestrator)


async def _run_single(orchestrator: Orchestrator, channel: str) -> str:
    return await orchestrator.run_once(channel)


async def _run_all(orchestrator: Orchestrator, progress: Progress, task) -> list[str]:
    job_ids = []
    for ch in ["horror", "facts", "finance"]:
        job_id = await orchestrator.run_once(ch)
        job_ids.append(job_id)
        progress.update(task, advance=1)
    return job_ids


def _show_job_summary(orchestrator: Orchestrator):
    jobs = orchestrator.get_recent_jobs(5)
    if not jobs:
        return

    table = Table(title="최근 작업", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("채널", style="magenta")
    table.add_column("상태")
    table.add_column("소요시간")

    for job in jobs:
        status_style = {
            JobStatus.COMPLETED: "[green]완료[/green]",
            JobStatus.FAILED: "[red]실패[/red]",
            JobStatus.RUNNING: "[yellow]실행중[/yellow]",
            JobStatus.PENDING: "[dim]대기[/dim]",
            JobStatus.RETRYING: "[yellow]재시도[/yellow]",
        }.get(job.status, str(job.status))

        duration = ""
        if job.started_at and job.completed_at:
            duration = f"{(job.completed_at - job.started_at).seconds}s"

        table.add_row(job.job_id, job.channel, status_style, duration)

    console.print(table)


@schedule_app.command("start")
def schedule_start(
    daemon: bool = typer.Option(False, "--daemon", "-d", help="데몬 모드"),
    dry_run: bool = typer.Option(False, "--dry-run", help="시뮬레이션 모드"),
):
    """스케줄러 시작."""
    dry_run = dry_run or _get_dry_run()
    orchestrator = get_orchestrator(dry_run=dry_run)

    console.print(Panel("[bold green]스케줄러 시작[/bold green]", subtitle="Ctrl+C로 중지"))

    settings = get_settings()
    schedules = {
        "horror": getattr(settings, "horror_schedule", "09:00"),
        "facts": getattr(settings, "facts_schedule", "12:00"),
        "finance": getattr(settings, "finance_schedule", "15:00"),
    }

    _show_schedule_table(schedules)

    try:
        asyncio.run(_run_scheduler(orchestrator, schedules))
    except KeyboardInterrupt:
        console.print("\n[yellow]스케줄러 중지됨[/yellow]")


async def _run_scheduler(orchestrator: Orchestrator, schedules: dict[str, str]):
    await orchestrator.start(schedules)
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await orchestrator.stop()


def _show_schedule_table(schedules: dict[str, str]):
    table = Table(title="스케줄 설정", show_header=True)
    table.add_column("채널", style="cyan")
    table.add_column("실행 시간", style="green")
    table.add_column("주기")

    for channel, time in schedules.items():
        table.add_row(channel.title(), time, "매일")

    console.print(table)


@schedule_app.command("stop")
def schedule_stop():
    """스케줄러 중지."""
    orchestrator = get_orchestrator()
    asyncio.run(orchestrator.stop())
    console.print("[green]스케줄러 중지됨[/green]")


@app.command()
def status():
    """현재 상태 확인."""
    orchestrator = get_orchestrator()
    state = orchestrator.status()

    table = Table(title="시스템 상태", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("값", style="green")

    table.add_row("상태", state["state"])
    table.add_row("대기 작업", str(state["pending_jobs"]))
    table.add_row("실행 중", str(state["running_jobs"]))
    table.add_row("전체 작업", str(state["total_jobs"]))
    table.add_row("워커 수", str(state["workers"]))
    table.add_row("Dry Run", "✓" if state["dry_run"] else "✗")

    console.print(table)

    if state["stats"]:
        stats_table = Table(title="채널별 통계", show_header=True)
        stats_table.add_column("채널", style="cyan")
        stats_table.add_column("완료", style="green")
        stats_table.add_column("실패", style="red")
        stats_table.add_column("전체")

        for channel, stats in state["stats"].items():
            stats_table.add_row(
                channel,
                str(stats["completed"]),
                str(stats["failed"]),
                str(stats["total"]),
            )

        console.print(stats_table)


@config_app.command("show")
def config_show():
    """설정 확인."""
    settings = get_settings()

    table = Table(title="현재 설정", show_header=True)
    table.add_column("설정", style="cyan")
    table.add_column("값", style="green")

    safe_fields = [
        "environment",
        "debug",
        "log_level",
        "output_dir",
        "llm_model",
        "tts_provider",
        "image_provider",
    ]

    for field in safe_fields:
        if hasattr(settings, field):
            table.add_row(field, str(getattr(settings, field)))

    api_keys = ["anthropic_api_key", "openai_api_key", "elevenlabs_api_key", "youtube_api_key"]
    for key in api_keys:
        if hasattr(settings, key) and getattr(settings, key):
            table.add_row(key, "********")

    console.print(table)


@app.command()
def version():
    """버전 확인."""
    from src import __version__
    console.print(f"[cyan]ytauto[/cyan] v{__version__}")


# =============================================================================
# YouTube 인증 관리
# =============================================================================

@youtube_app.command("auth")
def youtube_auth(
    force: bool = typer.Option(False, "--force", "-f", help="기존 토큰 무시하고 재인증"),
    headless: bool = typer.Option(False, "--headless", "-H", help="브라우저 없이 수동 인증 (URL 복사 방식)"),
):
    """YouTube OAuth 인증 실행."""
    from src.services.youtube.auth import YouTubeAuth
    from src.core.exceptions import YouTubeAuthError
    
    settings = get_settings()
    client_secrets_path = settings.youtube.client_secrets_file
    token_path = settings.youtube.token_file
    
    # client_secrets.json 존재 확인
    if not client_secrets_path.exists():
        console.print(Panel(
            "[bold red]client_secrets.json 파일이 없습니다![/bold red]\n\n"
            "YouTube 인증을 위해 Google Cloud Console에서 OAuth 자격 증명을 다운로드해야 합니다.\n\n"
            "[bold cyan]설정 방법:[/bold cyan]\n"
            "1. https://console.cloud.google.com/ 접속\n"
            "2. 프로젝트 생성 또는 선택\n"
            "3. 'API 및 서비스' → '사용자 인증 정보'\n"
            "4. 'OAuth 2.0 클라이언트 ID' 생성 (데스크톱 앱)\n"
            "5. JSON 다운로드 → config/client_secrets.json 으로 저장\n\n"
            f"[dim]경로: {client_secrets_path}[/dim]",
            title="⚠️ 설정 필요",
            border_style="red",
        ))
        raise typer.Exit(1)
    
    # 기존 토큰 확인
    if token_path.exists() and not force:
        console.print("[yellow]이미 인증되어 있습니다. 재인증하려면 --force 옵션을 사용하세요.[/yellow]")
        raise typer.Exit(0)
    
    # 기존 토큰 삭제 (force 모드)
    if force and token_path.exists():
        token_path.unlink()
        console.print("[dim]기존 토큰 삭제됨[/dim]")
    
    console.print(Panel(
        "[bold cyan]브라우저에서 Google 로그인 창이 열립니다.[/bold cyan]\n\n"
        "1. Google 계정으로 로그인\n"
        "2. YouTube 채널 접근 권한 승인\n"
        "3. 완료 후 이 창으로 돌아오세요",
        title="🔐 YouTube 인증",
        border_style="cyan",
    ))
    
    try:
        auth = YouTubeAuth()
        _ = auth.authenticate(headless=headless)
        
        console.print(Panel(
            "[bold green]✓ YouTube 인증 완료![/bold green]\n\n"
            f"토큰 저장됨: {token_path}",
            title="✅ 성공",
            border_style="green",
        ))
    except YouTubeAuthError as e:
        console.print(f"[red]인증 실패: {e}[/red]")
        raise typer.Exit(1)


@youtube_app.command("status")
def youtube_status():
    """YouTube 인증 상태 확인."""
    import json
    from datetime import datetime
    
    settings = get_settings()
    token_path = settings.youtube.token_file
    client_secrets_path = settings.youtube.client_secrets_file
    
    table = Table(title="YouTube 인증 상태", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("상태", style="green")
    table.add_column("상세")
    
    # client_secrets.json 확인
    if client_secrets_path.exists():
        table.add_row("client_secrets.json", "[green]✓ 있음[/green]", str(client_secrets_path))
    else:
        table.add_row("client_secrets.json", "[red]✗ 없음[/red]", "Google Cloud Console에서 다운로드 필요")
    
    # 토큰 파일 확인
    if token_path.exists():
        try:
            with open(token_path, "r") as f:
                token_data = json.load(f)
            
            expiry_str = token_data.get("expiry", "")
            if expiry_str:
                try:
                    expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                    now = datetime.now(expiry.tzinfo)
                    if expiry > now:
                        remaining = expiry - now
                        table.add_row("토큰", "[green]✓ 유효[/green]", f"만료까지 {remaining.seconds // 3600}시간 {(remaining.seconds % 3600) // 60}분")
                    else:
                        table.add_row("토큰", "[yellow]⚠ 만료됨[/yellow]", "자동 갱신됨")
                except Exception:
                    table.add_row("토큰", "[green]✓ 있음[/green]", "만료 시간 파싱 실패")
            else:
                table.add_row("토큰", "[green]✓ 있음[/green]", "만료 시간 없음")
            
            # 스코프 확인
            scopes = token_data.get("scopes", [])
            if scopes:
                scope_names = [s.split("/")[-1] for s in scopes]
                table.add_row("스코프", "[green]✓[/green]", ", ".join(scope_names))
            
        except json.JSONDecodeError:
            table.add_row("토큰", "[red]✗ 손상됨[/red]", "ytauto youtube auth 재실행 필요")
    else:
        table.add_row("토큰", "[red]✗ 없음[/red]", "ytauto youtube auth 실행 필요")
    
    console.print(table)


@youtube_app.command("revoke")
def youtube_revoke(
    confirm: bool = typer.Option(False, "--yes", "-y", help="확인 없이 삭제"),
):
    """YouTube 인증 토큰 삭제."""
    from src.services.youtube.auth import YouTubeAuth
    
    settings = get_settings()
    token_path = settings.youtube.token_file
    
    if not token_path.exists():
        console.print("[yellow]삭제할 토큰이 없습니다.[/yellow]")
        raise typer.Exit(0)
    
    if not confirm:
        confirm_input = typer.confirm("정말로 YouTube 인증을 취소하시겠습니까?")
        if not confirm_input:
            console.print("[dim]취소됨[/dim]")
            raise typer.Exit(0)
    
    try:
        auth = YouTubeAuth()
        success = auth.revoke()
        
        if success:
            console.print("[green]✓ YouTube 인증이 취소되었습니다.[/green]")
        else:
            # revoke API 실패해도 로컬 토큰은 삭제됨
            console.print("[yellow]⚠ Google 서버 취소 실패, 로컬 토큰은 삭제됨[/yellow]")
    except Exception as e:
        # 로컬 토큰만 삭제
        token_path.unlink(missing_ok=True)
        console.print(f"[yellow]⚠ 오류 발생, 로컬 토큰만 삭제됨: {e}[/yellow]")


def main():
    app()


if __name__ == "__main__":
    main()
