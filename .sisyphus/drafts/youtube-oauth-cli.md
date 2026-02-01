# Draft: YouTube OAuth CLI Implementation

## Requirements (confirmed)

- **CLI framework**: Typer + Rich (matching existing pattern)
- **Subcommand group**: `youtube_app = typer.Typer()` added to `app`
- **Commands to implement**:
  - `ytauto youtube auth` - Run OAuth flow, open browser
  - `ytauto youtube status` - Check token file + expiry (NO API call)
  - `ytauto youtube revoke` - Revoke token with confirmation

## Technical Decisions

- **Token status**: Simple file check + expiry date (no YouTube API call)
- **Pre-auth check**: Check `client_secrets.json` exists before OAuth flow, show friendly error with setup instructions
- **Documentation**: `docs/youtube-setup.md` (standalone, 한국어)
- **CLI messages**: 한국어 (matching existing style)

## Research Findings

### Existing CLI Pattern (from `src/cli.py`)
```python
schedule_app = typer.Typer(help="스케줄러 관리")
config_app = typer.Typer(help="설정 관리")
app.add_typer(schedule_app, name="schedule")
app.add_typer(config_app, name="config")
```

### YouTubeAuth Methods Available
- `credentials` property - Load/create credentials
- `youtube` property - Build youtube service
- `is_authenticated()` - Check if authenticated
- `revoke()` - Revoke token, returns bool
- `_run_oauth_flow()` - Internal: triggers browser auth
- `_load_token()` - Internal: loads from file
- `_save_token()` - Internal: saves to file

### Token File Path
- `config/youtube_token.json` (from `YouTubeSettings.token_file`)
- `config/client_secrets.json` (from `YouTubeSettings.client_secrets_file`)

## Scope Boundaries

### INCLUDE
- Add `youtube` subcommand group to CLI
- Implement 3 commands: auth, status, revoke
- Create `docs/youtube-setup.md` with Google Cloud Console guide
- Add pre-auth validation with user-friendly error

### EXCLUDE
- YouTube API calls in status command
- Modifying `YouTubeAuth` class (already complete)
- Multi-account support
- Token encryption

## Open Questions
(None - all clarified by user)

## Test Strategy Decision
- **Infrastructure exists**: Unknown - need to check
- **User wants tests**: Not specified
- **QA approach**: Manual CLI verification
