# Draft: YouTube 자동화 시스템 검증 및 설정

## Requirements (confirmed)
- data/ 디렉토리 구조 생성 (templates, assets/music, assets/fonts, output + .gitkeep)
- 누락된 부분 점검 (__init__.py, 순환 import, 타입 힌트, 인터페이스 구현)
- Dry-run 테스트 (Mock 데이터로 파이프라인 흐름 검증)
- 의존성 설치 + Import 검증 (pip install -e . 후 모든 모듈 import 테스트)

## Technical Decisions

### 현재 상태 분석
- **Python 파일**: 41개 완성
- **pyproject.toml**: 존재, 의존성 정의됨
- **data/ 디렉토리**: templates/, assets/, output/ 존재하나 비어있음 (.gitkeep 없음)
- **tests/ 디렉토리**: 존재하지 않음 (pytest 설정은 있음)
- **테스트 인프라**: pyproject.toml에 pytest 포함, 단 실제 테스트 파일 없음

### 발견된 이슈 (코드 리뷰)
1. **인터페이스 시그니처 불일치**:
   - FactsPipeline.run(channel: str) vs ContentPipeline.run(channel: ChannelType)
   - FactsPipeline.run_batch(channel: str, count) vs ContentPipeline.run_batch(channel: ChannelType, count)
   
2. **Orchestrator 문제**:
   - _lazy_load_pipeline에서 생성자 파라미터 없이 Pipeline 인스턴스화 시도
   - HorrorPipeline(), FactsPipeline(), FinancePipeline() - 필수 파라미터 누락

3. **data/ 구조**:
   - assets/music/ 없음
   - assets/fonts/ 없음
   - .gitkeep 파일 없음

## Research Findings
- explore 에이전트 4개 실행 중 (결과 대기)
- 테스트 인프라는 pyproject.toml에 설정됨 (pytest, pytest-asyncio)

## Open Questions
- 테스트 작성 여부 (TDD vs 테스트 없이 manual verification)
- Mock 서비스 구현 범위

## Scope Boundaries
- INCLUDE: data/ 구조, 점검, dry-run, import 검증
- EXCLUDE: 실제 API 연동 테스트, 새로운 기능 구현
