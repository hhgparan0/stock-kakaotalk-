"""매일 아침 공포지수 + 미국 반도체주 브리핑을 카카오톡 '나에게 보내기'로 발송.
GitHub Actions에서 실행됨. 외부 패키지 없이 표준 라이브러리만 사용.

필요한 환경변수(=GitHub Secrets):
  KAKAO_REST_API_KEY  : 카카오 디벨로퍼스 REST API 키
  KAKAO_REFRESH_TOKEN : talk_message 동의로 발급받은 refresh token
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

STOCKS = [("AVGO", "브로드컴"), ("AMD", ""), ("NVDA", "엔비디아"), ("SNDK", "샌디스크")]

RATING_KR = {
    "extreme fear": "극단적 공포",
    "fear": "공포",
    "neutral": "중립",
    "greed": "탐욕",
    "extreme greed": "극단적 탐욕",
}


def http_get_json(url, extra_headers=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post_json(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode("utf-8")
    h = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def get_fear_greed():
    """(점수, 영문등급) 반환. 실패 시 (None, None)."""
    try:
        # CNN(Akamai)은 Referer/Origin이 없으면 418로 막음
        data = http_get_json(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            extra_headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://edition.cnn.com",
                "Referer": "https://edition.cnn.com/",
            },
        )
        fg = data["fear_and_greed"]
        return round(float(fg["score"])), str(fg["rating"]).lower()
    except Exception as e:
        print("공포지수 조회 실패:", e)
        return None, None


def signal_for(score):
    if score is None:
        return "조회 실패"
    if score <= 25:
        return "🚨 강한 매수 신호"
    if score <= 44:
        return "⚠️ 매수 관심"
    return "신호 아님"


def get_quote(ticker):
    """(가격, 등락률%) 반환. 일일 등락률은 직전 거래일 두 종가로 계산."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
    data = http_get_json(url)
    res = data["chart"]["result"][0]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    price, prev = closes[-1], closes[-2]
    return price, (price - prev) / prev * 100


def fmt_price(p):
    return f"${p:,.2f}" if p < 1000 else f"${p:,.0f}"


def build_message():
    kst = datetime.now(timezone.utc) + timedelta(hours=9)
    score, rating = get_fear_greed()
    rating_kr = RATING_KR.get(rating, rating or "-")

    lines = [f"📊 주가 브리핑 {kst.month}/{kst.day}"]
    if score is not None:
        lines.append(f"😱 공포지수 {score} ({rating_kr}) — {signal_for(score)}")
    else:
        lines.append("😱 공포지수 조회 실패")

    lines.append("💻 미국 반도체 (전일 마감)")
    for tk, kr in STOCKS:
        try:
            price, chg = get_quote(tk)
            arrow = "🔺" if chg >= 0 else "🔻"
            name = f"{tk} {kr}".strip()
            lines.append(f"{name} {fmt_price(price)} {arrow}{abs(chg):.1f}%")
        except Exception as e:
            print(f"{tk} 조회 실패:", e)
            lines.append(f"{tk} 조회실패")
    return "\n".join(lines)


def send_kakao(text):
    rest_key = os.environ["KAKAO_REST_API_KEY"]
    refresh = os.environ["KAKAO_REFRESH_TOKEN"]

    payload = {
        "grant_type": "refresh_token",
        "client_id": rest_key,
        "refresh_token": refresh,
    }
    # 앱에 Client Secret이 '사용함'이면 모든 토큰 요청에 필요
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET")
    if client_secret:
        payload["client_secret"] = client_secret

    tok = http_post_json("https://kauth.kakao.com/oauth/token", payload)
    access = tok["access_token"]
    if "refresh_token" in tok:
        # 카카오가 만료 임박 시 새 refresh token을 재발급함 → 로그에 남겨 갱신 안내
        print("새 refresh_token 발급됨(만료 임박). GitHub Secret 갱신 필요할 수 있음:", tok["refresh_token"])

    template = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": "https://edition.cnn.com/markets/fear-and-greed",
            "mobile_web_url": "https://edition.cnn.com/markets/fear-and-greed",
        },
        "button_title": "공포지수 보기",
    }
    http_post_json(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        {"template_object": json.dumps(template, ensure_ascii=False)},
        headers={"Authorization": f"Bearer {access}"},
    )


def main():
    text = build_message()
    print(text)
    send_kakao(text)
    print("카카오톡 발송 완료")


if __name__ == "__main__":
    main()
