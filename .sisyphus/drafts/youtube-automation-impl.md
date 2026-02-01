# Draft: YouTube Faceless 자동화 시스템 구현

## Requirements (confirmed)

### 기존 코드베이스 (완료)
- `src/core/interfaces.py` - 9개 ABC 정의
  - ScriptGenerator, TTSEngine, ImageGenerator, VideoGenerator
  - MusicGenerator, VideoComposer, ThumbnailGenerator, YouTubeUploader, ContentPipeline
- `src/core/models.py` - 도메인 모델
  - ChannelType (HORROR/FACTS/FINANCE), Script, VideoProject, ChannelConfig
- `config/settings.py` - Pydantic 설정 시스템
- `src/core/exceptions.py` - 커스텀 예외

### 구현 대상 (TODO)
1. src/services/llm/ - LLM 클라이언트
2. src/services/tts/ - TTS 엔진
3. src/services/visual/ - 이미지/영상 생성기
4. src/services/video/ - FFmpeg 합성 파이프라인
5. src/services/thumbnail/ - 썸네일 생성기
6. src/services/youtube/ - YouTube API 업로더
7. src/channels/{horror,facts,finance}/ - 채널별 파이프라인
8. src/core/orchestrator.py - 스케줄러/큐잉/모니터링
9. src/cli.py - Typer CLI
10. __init__.py 파일들

## Technical Decisions

### 기술 스택 (확정)
- LLM: Claude (Anthropic) + GPT-4o (OpenAI)
- TTS: ElevenLabs (primary) + Edge TTS (fallback)
- Image: Replicate (SDXL) + DALL-E 3
- Video: Runway Gen-3
- Music: Suno API
- Video Composition: FFmpeg + MoviePy
- Upload: YouTube Data API v3

### 구현 패턴
- ABC 인터페이스 기반 구현
- async/await 비동기 처리
- tenacity 재시도 로직
- structlog 로깅
- Pydantic 설정 관리

## Scope Boundaries

### INCLUDE
- 10개 TODO 항목 전부 구현
- 3개 채널 파이프라인 (Horror, Facts, Finance)
- CLI 인터페이스
- 단위 테스트는 별도 계획

### EXCLUDE
- Docker 배포 설정
- 모니터링 대시보드 (별도)
- A/B 테스트 분석 (향후)
- 다국어 확장 (별도)

## Open Questions

1. 테스트 전략: TDD vs 구현 후 테스트?
2. Music Generator: Suno API 직접 구현 vs 스킵?
3. 각 서비스 fallback 전략 범위?

## Dependency Analysis

### Layer 1 (Foundation) - 병렬 가능
- LLM 클라이언트
- TTS 엔진
- 이미지 생성기 (부분)
- __init__.py 파일들

### Layer 2 (Requires Layer 1)
- 비디오 생성기 (이미지 필요)
- 썸네일 생성기 (이미지 생성 기반)
- 비디오 합성기 (TTS + 이미지 필요)

### Layer 3 (Requires Layer 2)
- YouTube 업로더 (독립)
- 채널별 파이프라인 (모든 서비스 필요)

### Layer 4 (Requires Layer 3)
- Orchestrator (파이프라인 필요)
- CLI (Orchestrator 필요)
