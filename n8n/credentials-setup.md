# n8n Credentials Setup Guide

n8n.jclee.me에서 설정해야 할 Credentials 목록

## 1. OpenAI API

**Type:** OpenAI API  
**Name:** `OpenAI API`

| Field   | Value                            |
| ------- | -------------------------------- |
| API Key | `sk-...` (OpenAI Dashboard에서 발급) |

## 2. ElevenLabs API

**Type:** Header Auth  
**Name:** `ElevenLabs API`

| Field        | Value               |
| ------------ | ------------------- |
| Header Name  | `xi-api-key`        |
| Header Value | ElevenLabs API Key  |

## 3. Replicate API

**Type:** Header Auth  
**Name:** `Replicate API`

| Field        | Value               |
| ------------ | ------------------- |
| Header Name  | `Authorization`     |
| Header Value | `Token r8_...`      |

## 4. YouTube OAuth2

**Type:** YouTube OAuth2 API  
**Name:** `YouTube OAuth2`

| Field         | Value                                                 |
| ------------- | ----------------------------------------------------- |
| Client ID     | Google Cloud Console에서 발급                          |
| Client Secret | Google Cloud Console에서 발급                          |
| Scope         | `https://www.googleapis.com/auth/youtube.upload`      |

### YouTube API 설정 순서:
1. Google Cloud Console → APIs & Services → Enable YouTube Data API v3
2. OAuth Consent Screen 설정 (External → Test users 추가)
3. Credentials → OAuth 2.0 Client ID 생성
4. n8n에서 OAuth 연결

## 5. MinIO S3

**Type:** S3  
**Name:** `MinIO S3`

| Field              | Value                           |
| ------------------ | ------------------------------- |
| Access Key ID      | MinIO admin access key          |
| Secret Access Key  | MinIO admin secret key          |
| Region             | `us-east-1` (기본값)             |
| Custom Endpoint    | `https://minio.jclee.me` 또는 `http://192.168.50.109:9000` |
| Force Path Style   | ✅ Yes                          |

## 6. Supabase PostgreSQL

**Type:** PostgreSQL  
**Name:** `Supabase PostgreSQL`

| Field    | Value                                    |
| -------- | ---------------------------------------- |
| Host     | `db.xxxxxxxxx.supabase.co`               |
| Database | `postgres`                               |
| User     | `postgres`                               |
| Password | Supabase 대시보드에서 확인                |
| Port     | `5432` (또는 `6543` for pooler)          |
| SSL      | ✅ Require                               |

또는 내부 네트워크:

| Field    | Value                |
| -------- | -------------------- |
| Host     | `192.168.50.107`     |
| Database | `postgres`           |
| User     | `postgres`           |
| Password | 설정된 비밀번호        |
| Port     | `5432`               |

## 7. Slack API (Optional)

**Type:** Slack API  
**Name:** `Slack API`

| Field       | Value                               |
| ----------- | ----------------------------------- |
| Access Token | `xoxb-...` (Slack App Bot Token)   |

### Slack App 설정:
1. api.slack.com → Create New App
2. OAuth & Permissions → Bot Token Scopes: `chat:write`
3. Install to Workspace
4. Copy Bot User OAuth Token

## Credentials 확인

n8n에서 각 credential 생성 후:
1. Test Connection 버튼 클릭
2. 연결 성공 확인
3. 워크플로우에서 credential 선택

## 필수 순서

1. ✅ OpenAI API (LLM)
2. ✅ ElevenLabs API (TTS)
3. ✅ Replicate API (Images)
4. ✅ MinIO S3 (Storage)
5. ✅ Supabase PostgreSQL (DB)
6. ✅ YouTube OAuth2 (Upload)
7. ⬜ Slack API (Notifications - Optional)
