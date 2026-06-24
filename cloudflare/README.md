# stock-kakao-cron (Cloudflare Worker, 옵션 B-1)

평일 KST 10:07 / 14:07 에 Cloudflare Worker cron이 GitHub Actions의 `daily-briefing.yml`을 `workflow_dispatch`로 호출.

## 구성
- `wrangler.toml` — cron 2개 + GH 레포/워크플로우 변수
- `src/index.ts` — `scheduled()` 핸들러가 GitHub API 호출, `fetch()` 핸들러로 수동 테스트 가능
- 시크릿: `GH_PAT` 1개만 필요 (`wrangler secret put GH_PAT`)

## 셋업

### 1. GitHub PAT 발급
- https://github.com/settings/tokens?type=beta (Fine-grained 권장)
- Repository access: `hhgparan0/stock-kakaotalk-` 만 선택
- Permissions → Repository → **Actions: Read and write**
- Expiration: 1년 (또는 원하는 만큼)
- 발급된 토큰 복사

### 2. 의존성 설치
```powershell
cd "C:\Users\hhg98\Downloads\클로드코드\주식-cloudflare"
npm install
```

### 3. Cloudflare 로그인
```powershell
npx wrangler login
```

### 4. 시크릿 등록
```powershell
npx wrangler secret put GH_PAT
# 프롬프트에 PAT 붙여넣기
```

### 5. 배포
```powershell
npx wrangler deploy
```

### 6. 수동 테스트
배포 후 출력되는 URL로:
```
https://stock-kakao-cron.<your-subdomain>.workers.dev/?market=us
https://stock-kakao-cron.<your-subdomain>.workers.dev/?market=kr
```
→ GitHub Actions에 새 run 떠야 함. 카톡 도착 확인.

### 7. 검증 후 GitHub Actions schedule 비활성화
`daily-briefing.yml`에서 `schedule:` 블록 제거하고 `workflow_dispatch:`만 남기기.

## 모니터링
```powershell
npx wrangler tail
```
실시간 로그 확인 (scheduled / fetch 호출).

## cron 시각 매핑
| Worker cron (UTC) | KST | 시장 |
|---|---|---|
| `7 1 * * 1-5` | 평일 10:07 | us |
| `7 5 * * 1-5` | 평일 14:07 | kr |
