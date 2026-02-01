# YouTube OAuth 설정 가이드

이 가이드는 YouTube 자동 업로드를 위한 OAuth 2.0 인증 설정 방법을 설명합니다.

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 상단의 프로젝트 선택 드롭다운 클릭
3. **새 프로젝트** 클릭
4. 프로젝트 이름 입력 (예: `youtube-automation`)
5. **만들기** 클릭

### 1.2 YouTube Data API 활성화

1. 좌측 메뉴에서 **API 및 서비스** → **라이브러리**
2. 검색창에 `YouTube Data API v3` 입력
3. **YouTube Data API v3** 선택
4. **사용** 버튼 클릭
5. (선택) **YouTube Analytics API**도 동일하게 활성화

### 1.3 OAuth 동의 화면 설정

1. 좌측 메뉴에서 **API 및 서비스** → **OAuth 동의 화면**
2. 사용자 유형: **외부** 선택 → **만들기**
3. 앱 정보 입력:
   - 앱 이름: `YouTube Automation`
   - 사용자 지원 이메일: 본인 이메일
   - 개발자 연락처 정보: 본인 이메일
4. **저장 후 계속**
5. 범위 추가:
   - `.../auth/youtube.upload` (동영상 업로드)
   - `.../auth/youtube` (채널 관리)
   - `.../auth/youtube.readonly` (읽기 전용)
   - `.../auth/yt-analytics.readonly` (분석 읽기)
6. **저장 후 계속**
7. 테스트 사용자 추가: 본인 Gmail 주소 입력
8. **저장 후 계속** → **대시보드로 돌아가기**

> ⚠️ **중요**: 테스트 모드에서는 테스트 사용자로 등록된 계정만 인증 가능합니다.

### 1.4 OAuth 클라이언트 ID 생성

1. 좌측 메뉴에서 **API 및 서비스** → **사용자 인증 정보**
2. 상단의 **+ 사용자 인증 정보 만들기** → **OAuth 클라이언트 ID**
3. 애플리케이션 유형: **데스크톱 앱** 선택
4. 이름: `ytauto-desktop`
5. **만들기** 클릭
6. **JSON 다운로드** 버튼 클릭

### 1.5 client_secrets.json 저장

다운로드한 JSON 파일을 프로젝트의 `config/` 디렉토리에 저장:

```bash
# 다운로드한 파일을 이동
mv ~/Downloads/client_secret_*.json /home/jclee/dev/money/config/client_secrets.json
```

파일 구조 확인:
```
/home/jclee/dev/money/
└── config/
    └── client_secrets.json   # ← 여기에 저장
```

## 2. YouTube 인증 실행

### 2.1 인증 시작

```bash
cd /home/jclee/dev/money
source .venv/bin/activate
ytauto youtube auth
```

브라우저가 자동으로 열리며:
1. Google 계정으로 로그인
2. `YouTube Automation` 앱의 권한 요청 승인
3. "인증 성공" 메시지 확인

### 2.2 인증 상태 확인

```bash
ytauto youtube status
```

출력 예시:
```
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 항목                 ┃ 상태    ┃ 상세                   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ client_secrets.json │ ✓ 있음 │ config/client_secrets.json │
│ 토큰                │ ✓ 유효 │ 만료까지 23시간 45분    │
│ 스코프              │ ✓      │ youtube.upload, youtube │
└─────────────────────┴─────────┴────────────────────────┘
```

### 2.3 인증 취소

```bash
# 확인 프롬프트 표시
ytauto youtube revoke

# 확인 없이 바로 취소
ytauto youtube revoke --yes
```

## 3. 문제 해결

### 3.1 "client_secrets.json 파일이 없습니다" 오류

1. Google Cloud Console에서 JSON 다운로드 완료 확인
2. 파일이 `config/client_secrets.json` 경로에 있는지 확인
3. 파일명이 정확히 `client_secrets.json`인지 확인

### 3.2 "access_denied" 오류

1. OAuth 동의 화면에서 테스트 사용자로 본인 이메일 추가 확인
2. 앱이 "테스트 모드"인 경우 테스트 사용자만 인증 가능

### 3.3 "redirect_uri_mismatch" 오류

1. OAuth 클라이언트 ID 유형이 **데스크톱 앱**인지 확인
2. 웹 애플리케이션 유형으로 생성했다면 삭제 후 재생성

### 3.4 토큰 만료

토큰은 자동으로 갱신됩니다. 수동 재인증이 필요한 경우:

```bash
ytauto youtube auth --force
```

### 3.5 권한 부족 오류

OAuth 동의 화면에서 필요한 스코프가 모두 추가되었는지 확인:
- `youtube.upload`
- `youtube`
- `youtube.readonly`
- `yt-analytics.readonly`

## 4. 보안 주의사항

⚠️ **절대 공유하지 마세요:**
- `config/client_secrets.json` - OAuth 클라이언트 비밀키
- `config/youtube_token.json` - 인증 토큰

`.gitignore`에 이미 추가되어 있습니다:
```
config/client_secrets.json
config/youtube_token.json
```

## 5. 다음 단계

인증 완료 후:

```bash
# 실제 영상 생성 테스트 (API 키 필요)
ytauto run --channel horror

# 스케줄러 시작
ytauto schedule start
```
