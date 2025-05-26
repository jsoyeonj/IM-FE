import json
import requests
import datetime
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

# 백엔드 API 설정
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000')  # 백엔드 서버 주소

# 리다이렉트 URI 설정 (환경변수 또는 기본값)
REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

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

    # 디버깅 정보
    print(f"사용할 리다이렉트 URI: {REDIRECT_URI}")

    # Google에 요청할 정보 지정
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=REDIRECT_URI,
        scope=["openid", "email", "profile"],
    )

    return request_uri


def send_user_to_backend(google_user_info):
    """구글 사용자 정보를 백엔드 API로 전송하여 회원가입/로그인 처리"""
    try:
        # 구글 사용자 정보에서 백엔드 DB에 필요한 데이터만 추출
        user_data = {
            'id': google_user_info.get('sub'),  # 구글 ID (google_id로 저장됨)
            'name': google_user_info.get('name', '사용자')  # 사용자 이름
        }
        
        print(f"백엔드로 전송할 사용자 데이터: {user_data}")
        
        # 백엔드 API 호출 - 올바른 URL 경로 사용
        backend_url = f"{BACKEND_API_URL}/auth/google/callback"  # 수정된 경로
        
        print(f"백엔드 요청 URL: {backend_url}")
        
        # POST 요청으로 사용자 정보 직접 전송
        response = requests.post(
            backend_url,
            json={'user_info': user_data},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"백엔드 응답 상태코드: {response.status_code}")
        print(f"백엔드 응답 내용: {response.text}")
        
        if response.status_code == 200:
            backend_data = response.json()
            print(f"백엔드 파싱된 데이터: {backend_data}")
            
            if backend_data.get('success'):
                # 백엔드에서 JWT 토큰을 받았을 경우
                data = backend_data.get('data', {})
                jwt_token = data.get('accessToken')
                
                print(f"백엔드에서 받은 JWT 토큰: {jwt_token}")
                
                if jwt_token:
                    return True, jwt_token
                else:
                    print("백엔드 응답에 accessToken이 없습니다.")
                    return False, "백엔드에서 토큰을 받지 못했습니다."
            else:
                return False, f"백엔드 로그인 실패: {backend_data.get('message', '알 수 없는 오류')}"
        elif response.status_code == 404:
            print("❌ 백엔드 API 엔드포인트를 찾을 수 없습니다.")
            return False, "백엔드 API 엔드포인트가 존재하지 않습니다."
        elif response.status_code == 500:
            print("❌ 백엔드 서버 내부 오류가 발생했습니다.")
            return False, "백엔드 서버 내부 오류"
        else:
            return False, f"백엔드 서버 오류: {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        print(f"백엔드 API 호출 오류: {str(e)}")
        return False, f"백엔드 서버 연결 오류: {str(e)}"
    except Exception as e:
        print(f"백엔드 전송 중 예외 발생: {str(e)}")
        return False, f"백엔드 처리 중 오류: {str(e)}"


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

    # 인증 코드로 토큰 요청
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=REDIRECT_URI,  # 환경변수 사용
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

        google_user_info = userinfo_response.json()
        print(f"구글에서 받은 사용자 정보: {google_user_info}")

        # 이메일이 확인되었는지 검증
        if google_user_info.get("email_verified"):
            # 기존 세션 저장 로직
            unique_id = google_user_info["sub"]
            users_email = google_user_info["email"]
            picture = google_user_info.get("picture", "")
            users_name = google_user_info.get("name", "사용자")

            # 세션에 사용자 정보 저장
            session["user_id"] = unique_id
            session["user_email"] = users_email
            session["user_name"] = users_name
            session["user_picture"] = picture
            session["logged_in"] = True

            # 백엔드 API로 사용자 정보 전송
            backend_success, backend_result = send_user_to_backend(google_user_info)
            
            if backend_success:
                print(f"✅ 백엔드 로그인 성공. JWT 토큰: {backend_result}")
                # JWT 토큰을 세션에 저장 (키 이름 통일)
                session["access_token"] = backend_result
                session["jwt_token"] = backend_result     # 호환성을 위해 둘 다 저장
                print(f"세션에 토큰 저장 완료: access_token={backend_result[:20]}...")
                return True, None
            else:
                print(f"⚠️ 백엔드 저장 실패: {backend_result}")
                # 백엔드 실패해도 프론트엔드 로그인은 성공으로 처리
                # 임시 토큰 생성 (개발 환경용)
                fake_token = f"local_token_{unique_id}_{int(datetime.datetime.now().timestamp())}"
                session["access_token"] = fake_token
                session["jwt_token"] = fake_token
                print(f"⚠️ 임시 로컬 토큰 생성: {fake_token[:20]}...")
                return True, None

        return False, "사용자 이메일이 인증되지 않았습니다."

    except Exception as e:
        print(f"OAuth 인증 과정에서 오류 발생: {str(e)}")
        return False, f"OAuth 인증 과정에서 오류가 발생했습니다: {str(e)}"