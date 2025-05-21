import json
import requests
from flask import redirect, request, url_for, session
from oauthlib.oauth2 import WebApplicationClient
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
# 개발 환경에서는 HTTPS 요구사항 비활성화 (로컬 개발용)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Google OAuth 설정
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# OAuth 클라이언트 설정
client = WebApplicationClient(GOOGLE_CLIENT_ID)


def get_google_provider_cfg():
    """Google의 OAuth 구성 정보 얻기"""
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except Exception as e:
        print(f"Google Discovery URL 연결 오류: {e}")
        return None


def get_google_login_url():
    """Google 로그인 URL 생성"""
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return None

    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # 디버깅 - 상세 정보 출력
    print(f"요청 URL: {request.url}")
    print(f"URL 루트: {request.url_root}")
    print(f"스키마: {request.scheme}")
    print(f"호스트: {request.host}")

    # 하드코딩된 리디렉션 URI 사용
    redirect_uri = "http://localhost:5000/auth/google/callback"
    print(f"최종 리디렉션 URI: {redirect_uri}")

    # Google에 요청할 정보 지정
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=["openid", "email", "profile"],
    )

    return request_uri


def handle_google_callback():
    """Google에서 돌아온 콜백 처리"""
    # Google에서 전달된 코드 받기
    code = request.args.get("code")

    # 코드가 없으면 로그인 실패
    if not code:
        return False, "인증 코드가 없습니다."

    # Google OAuth 구성 정보 가져오기
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return False, "Google 인증 서버에 연결할 수 없습니다."

    token_endpoint = google_provider_cfg["token_endpoint"]

    # 하드코딩된 URI - get_google_login_url()과 동일하게 유지
    redirect_uri = "http://localhost:5000/auth/google/callback"

    # 인증 코드로 토큰 요청
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=redirect_uri,
        code=code
    )

    try:
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # 토큰 파싱
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Google에서 사용자 정보 가져오기
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        # 이메일이 확인되었는지 검증
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json()["sub"]
            users_email = userinfo_response.json()["email"]
            picture = userinfo_response.json().get("picture", "")
            users_name = userinfo_response.json().get("given_name", "사용자")

            # 세션에 사용자 정보 저장
            session["user_id"] = unique_id
            session["user_email"] = users_email
            session["user_name"] = users_name
            session["user_picture"] = picture
            session["logged_in"] = True

            return True, None

        return False, "사용자 이메일이 인증되지 않았습니다."

    except Exception as e:
        return False, f"OAuth 인증 과정에서 오류가 발생했습니다: {str(e)}"

    try:
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # 토큰 파싱
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Google에서 사용자 정보 가져오기
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        # 이메일이 확인되었는지 검증
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json()["sub"]
            users_email = userinfo_response.json()["email"]
            picture = userinfo_response.json().get("picture", "")
            users_name = userinfo_response.json().get("given_name", "사용자")

            # 세션에 사용자 정보 저장
            session["user_id"] = unique_id
            session["user_email"] = users_email
            session["user_name"] = users_name
            session["user_picture"] = picture
            session["logged_in"] = True

            return True, None

        return False, "사용자 이메일이 인증되지 않았습니다."

    except Exception as e:
        return False, f"OAuth 인증 과정에서 오류가 발생했습니다: {str(e)}"

    try:
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # 토큰 파싱
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Google에서 사용자 정보 가져오기
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        # 이메일이 확인되었는지 검증
        if userinfo_response.json().get("email_verified"):
            unique_id = userinfo_response.json()["sub"]
            users_email = userinfo_response.json()["email"]
            picture = userinfo_response.json().get("picture", "")
            users_name = userinfo_response.json().get("given_name", "사용자")

            # 세션에 사용자 정보 저장
            session["user_id"] = unique_id
            session["user_email"] = users_email
            session["user_name"] = users_name
            session["user_picture"] = picture
            session["logged_in"] = True

            return True, None

        return False, "사용자 이메일이 인증되지 않았습니다."

    except Exception as e:
        return False, f"OAuth 인증 과정에서 오류가 발생했습니다: {str(e)}"