from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
import datetime
import json
import uuid
import requests
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import secrets
import random

# .env 파일 로드
load_dotenv()
# 개발 환경에서는 HTTPS 요구사항 비활성화 (로컬 개발용)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# 백엔드 API URL 설정
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:8000/api')

# 음악 데이터를 저장할 JSON 파일 경로 (백엔드 연결 실패 시 사용)
MUSIC_DATA_FILE = 'music_data.json'

# Google OAuth 설정
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# 기본 앱 설정
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MUSIC_FOLDER'] = 'static/music'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'ogg'}

# uploads 폴더가 없으면 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# music 폴더가 없으면 생성
if not os.path.exists(app.config['MUSIC_FOLDER']):
    os.makedirs(app.config['MUSIC_FOLDER'])

# 이미지 폴더 확인 및 생성
if not os.path.exists('static/images'):
    os.makedirs('static/images')

# Google OAuth 도우미 가져오기
from oauth_helper import get_google_login_url, handle_google_callback


def get_auth_headers():
    """인증 헤더 반환 - 개선된 버전"""
    headers = {'Content-Type': 'application/json'}

    # JWT 토큰 확인 (두 키 모두 확인)
    access_token = session.get('access_token') or session.get('jwt_token')

    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
        print(f"🔑 JWT 토큰 사용: Bearer {access_token[:20]}...")
    else:
        print("⚠️ JWT 토큰이 없습니다. 익명 사용자로 처리됩니다.")
        print(f"세션 내용: user_id={session.get('user_id')}, logged_in={session.get('logged_in')}")
        print(f"세션 키들: {list(session.keys())}")

    return headers


def is_user_logged_in():
    """사용자 로그인 상태 확인"""
    logged_in = session.get('logged_in', False)
    access_token = session.get('access_token') or session.get('jwt_token')

    print(f"로그인 상태: {logged_in}, 토큰 존재: {access_token is not None}")

    if logged_in and not access_token:
        print("⚠️ 로그인은 되어있지만 JWT 토큰이 없습니다. 세션 문제일 수 있습니다.")

    return logged_in and access_token is not None


def check_backend_connection():
    """백엔드 서버 연결 확인"""
    try:
        print(f"백엔드 연결 시도: {BACKEND_API_URL}/health")
        response = requests.get(f'{BACKEND_API_URL}/health', timeout=5)
        print(f"백엔드 응답: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"백엔드 상태: 연결 성공")
            return True
        else:
            print(f"백엔드 오류 응답: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("백엔드 연결 실패: 서버가 실행되지 않았습니다.")
        return False
    except Exception as e:
        print(f"백엔드 연결 오류: {e}")
        return False


def load_music_data():
    """음악 데이터 로드 (로컬 JSON 파일)"""
    if os.path.exists(MUSIC_DATA_FILE):
        with open(MUSIC_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_music_data(data):
    """음악 데이터 저장 (로컬 JSON 파일)"""
    with open(MUSIC_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# 날짜 형식 포맷터
@app.template_filter('format_date')
def format_date(value, format='%Y년 %m월 %d일 %H:%M'):
    if isinstance(value, str):
        try:
            # ISO format 시도
            value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                # GMT format 시도 ('Mon, 26 May 2025 03:36:17 GMT')
                value = datetime.datetime.strptime(value, '%a, %d %b %Y %H:%M:%S %Z')
            except ValueError:
                try:
                    # 다른 일반적인 형식들 시도
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                        try:
                            value = datetime.datetime.strptime(value, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        # 모든 형식이 실패하면 현재 시간 사용
                        print(f"날짜 형식 변환 실패: {value}")
                        value = datetime.datetime.now()
                except:
                    value = datetime.datetime.now()
    return value.strftime(format)


@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')


@app.route('/create', methods=['GET', 'POST'])
def create():
    """음악 생성 페이지"""
    if request.method == 'POST':
        return redirect(url_for('generate_music'))

    # GET 요청인 경우 페이지 렌더링
    return render_template('create.html')


# 기존 /generate-music 라우트를 수정
@app.route('/generate-music', methods=['POST'])
def generate_music():
    """기본 설정 저장 - 실제 음악 생성하지 않고 다음 단계로"""
    try:
        data = request.get_json()
        print(f"기본 설정 저장 요청: {data}")

        # 필수 파라미터 확인
        if not data or 'mood' not in data or 'location' not in data:
            return jsonify({
                'success': False,
                'error': '분위기와 장소 정보가 필요합니다.'
            }), 400

        # 설정값을 세션에 저장 (음악 생성하지 않음)
        session['music_settings'] = {
            'speed': data.get('speed', 50),
            'mood': data.get('mood'),
            'location': data.get('location')
        }

        print(f"✓ 기본 설정 세션에 저장: {session['music_settings']}")

        # 임시 ID 생성 (실제 음악은 아직 생성되지 않음)
        temp_id = str(uuid.uuid4())

        return jsonify({
            'success': True,
            'music_id': temp_id,
            'next_step': url_for('detail_input', music_id=temp_id)
        })

    except Exception as e:
        print(f"기본 설정 저장 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


# 기존 /generate-music-with-detail을 실제 음악 생성으로 수정
@app.route('/generate-music-with-detail', methods=['POST'])
def generate_music_with_detail():
    """실제 음악 생성 - 기본 설정 + 상세 내용 통합"""
    try:
        data = request.get_json()
        print(f"최종 음악 생성 요청: {data}")

        if 'detail_text' not in data:
            return jsonify({
                'success': False,
                'error': '상세 내용이 필요합니다'
            }), 400

        detail_text = data.get('detail_text')
        music_id = data.get('music_id', '')

        # 세션에서 기본 설정 불러오기
        music_settings = session.get('music_settings', {})
        print(f"저장된 기본 설정: {music_settings}")

        # 로그인 상태 확인
        user_logged_in = is_user_logged_in()
        print(f"👤 사용자 로그인 상태: {user_logged_in}")

        # 통합된 프롬프트 생성
        if music_settings:
            prompt1 =  f"{music_settings.get('mood', '')} 분위기의 {music_settings.get('location', '')} 음악, 템포 {music_settings.get('speed')}"
            prompt2 = f"{detail_text}" 
        else:
            prompt1 = detail_text

        print(f"통합된 프롬프트: {prompt2}")

        # 백엔드 연결 확인 및 시도
        if check_backend_connection():
            try:
                api_data = {
                    'prompt1': prompt1,
                    'prompt2': prompt2
                }

                response = requests.post(
                    f'{BACKEND_API_URL}/generate-music',
                    json=api_data,
                    headers=get_auth_headers(),
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        music_data = result.get('data', {})
                        new_music_id = str(uuid.uuid4())

                        print(f"✓ 백엔드에서 최종 음악 생성 성공: {music_data.get('title')}")

                        # 세션에서 설정값 제거
                        session.pop('music_settings', None)

                        return jsonify({
                            'success': True,
                            'music_id': new_music_id,
                            'music_url': music_data.get('musicUrl'),
                            'title': music_data.get('title'),
                            'redirect_url': url_for('generation_complete', music_id=new_music_id)
                        })
                else:
                    print(f"백엔드 음악 생성 오류: {response.status_code} - {response.text}")
            except requests.RequestException as e:
                print(f"백엔드 요청 오류: {e}")

        # 로컬 처리 (백엔드 연결 실패 시)
        if not music_id:
            music_id = str(uuid.uuid4())

        created_at = datetime.datetime.now().isoformat()

        new_music_data = {
            'id': music_id,
            'title': f"{detail_text[:30]}{'...' if len(detail_text) > 30 else ''}",
            'full_prompt': prompt1,
            'detail_text': detail_text,
            'original_settings': music_settings,
            'created_at': created_at,
            'file_path': f'{music_id}.mp3',
            'user_id': session.get('user_id', 'anonymous')
        }

        music_list = load_music_data()

        # 기존 임시 데이터가 있으면 교체, 없으면 새로 추가
        existing_index = -1
        for i, music in enumerate(music_list):
            if music['id'] == music_id:
                existing_index = i
                break

        if existing_index >= 0:
            music_list[existing_index] = new_music_data
        else:
            music_list.append(new_music_data)

        save_music_data(music_list)

        # 세션에서 설정값 제거
        session.pop('music_settings', None)

        print(f"✓ 로컬에 최종 음악 데이터 저장: {new_music_data['title']}")

        return jsonify({
            'success': True,
            'music_id': music_id,
            'redirect_url': url_for('generation_complete', music_id=music_id)
        })

    except Exception as e:
        print(f"최종 음악 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


@app.route('/generate-music-from-image', methods=['POST'])
def generate_music_from_image():
    """이미지 기반 음악 생성"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '이미지 파일이 필요합니다'
            }), 400

        image_file = request.files['image']

        if image_file.filename == '':
            return jsonify({
                'success': False,
                'error': '파일이 선택되지 않았습니다'
            }), 400

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not ('.' in image_file.filename and
                image_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': '허용되지 않는 파일 형식입니다'
            }), 400

        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                files = {'image': (image_file.filename, image_file, image_file.content_type)}
                headers = {}
                if 'access_token' in session:
                    headers['Authorization'] = f'Bearer {session["access_token"]}'

                response = requests.post(
                    f'{BACKEND_API_URL}/generate-music/image',
                    files=files,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        music_data = result.get('data', {})
                        music_id = str(uuid.uuid4())

                        return jsonify({
                            'success': True,
                            'music_id': music_id,
                            'music_url': music_data.get('musicUrl'),
                            'title': music_data.get('title'),
                            'redirect_url': url_for('generation_complete', music_id=music_id)
                        })
            except requests.RequestException:
                pass

        # 로컬 처리 (백엔드 연결 실패 시)
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        user_id = session.get('user_id', 'anonymous')
        title = f"이미지 음악 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        music_id = str(uuid.uuid4())

        new_music = {
            'id': music_id,
            'user_id': user_id,
            'title': title,
            'mood': "이미지 기반",
            'location': "이미지",
            'tempo': random.randint(60, 180),
            'file_path': f"music_{music_id}.mp3",
            'created_at': datetime.datetime.now().isoformat()
        }

        music_list = load_music_data()
        music_list.append(new_music)
        save_music_data(music_list)

        return jsonify({
            'success': True,
            'music_id': music_id,
            'redirect_url': url_for('generation_complete', music_id=music_id)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


@app.route('/generate-music-from-video', methods=['POST'])
def generate_music_from_video():
    """동영상 기반 음악 생성"""
    # 이미지 처리와 동일한 로직 적용
    try:
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'error': '동영상 파일이 필요합니다'
            }), 400

        video_file = request.files['video']

        if video_file.filename == '':
            return jsonify({
                'success': False,
                'error': '파일이 선택되지 않았습니다'
            }), 400

        allowed_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
        if not ('.' in video_file.filename and
                video_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': '허용되지 않는 파일 형식입니다'
            }), 400

        # 로컬 처리 (백엔드 없이)
        filename = secure_filename(video_file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(video_path)

        user_id = session.get('user_id', 'anonymous')
        title = f"동영상 음악 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        music_id = str(uuid.uuid4())

        new_music = {
            'id': music_id,
            'user_id': user_id,
            'title': title,
            'mood': "동영상 기반",
            'location': "동영상",
            'tempo': random.randint(60, 180),
            'file_path': f"music_{music_id}.mp3",
            'created_at': datetime.datetime.now().isoformat(),
            'source_type': 'video'
        }

        music_list = load_music_data()
        music_list.append(new_music)
        save_music_data(music_list)

        return jsonify({
            'success': True,
            'music_id': music_id,
            'redirect_url': url_for('generation_complete', music_id=music_id)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


@app.route('/playlist')
def playlist():
    """플레이리스트 페이지"""
    try:
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()

                if 'access_token' in session:
                    response = requests.get(
                        f'{BACKEND_API_URL}/myplaylist',
                        headers=headers,
                        timeout=10
                    )
                else:
                    response = requests.get(
                        f'{BACKEND_API_URL}/playlist',
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        data = result.get('data', {})
                        music_list = data.get('musicList', [])

                        # 백엔드 데이터 형식에 맞게 변환
                        converted_music_list = []
                        for music in music_list:
                            converted_music = {
                                'id': music.get('id'),
                                'title': music.get('title'),
                                'music_url': music.get('musicUrl'),
                                'created_at': music.get('createdAt'),  # 날짜 형식 그대로 사용
                                'user_id': session.get('user_id', 'anonymous')
                            }
                            converted_music_list.append(converted_music)

                        music_list = converted_music_list

                        music_id = request.args.get('music_id')
                        selected_music = None
                        if music_id:
                            for music in music_list:
                                if str(music.get('id')) == music_id:
                                    selected_music = music
                                    break

                        print(f"✓ 백엔드에서 플레이리스트 로드 성공: {len(music_list)}개 음악")
                        return render_template('playlist.html', music_list=music_list, music=selected_music)
            except requests.RequestException as e:
                print(f"백엔드 플레이리스트 요청 오류: {e}")
            except Exception as e:
                print(f"백엔드 플레이리스트 처리 오류: {e}")

        # 로컬 데이터 사용
        print("백엔드 연결 실패. 로컬 플레이리스트를 사용합니다.")
        music_list = load_music_data()

        # 로그인한 사용자의 음악만 필터링
        if 'user_id' in session:
            music_list = [music for music in music_list if music['user_id'] == session['user_id']]

        # 생성일 기준 내림차순 정렬 (created_at이 있는 경우에만)
        music_list = [music for music in music_list if 'created_at' in music]
        music_list.sort(key=lambda x: x['created_at'], reverse=True)

        # URL 파라미터에서 music_id 확인하여 선택된 음악 찾기
        music_id = request.args.get('music_id')
        selected_music = None
        if music_id:
            for music in music_list:
                if music['id'] == music_id:
                    selected_music = music
                    break

        return render_template('playlist.html', music_list=music_list, music=selected_music)

    except Exception as e:
        print(f"플레이리스트 로드 오류: {e}")
        return render_template('playlist.html', music_list=[], music=None)


# app.py의 playlist_main 라우트를 다음과 같이 수정하세요
@app.route('/playlist-main')
def playlist_main():
    """메인 플레이리스트 페이지 (실시간 생성 + 인기 음악)"""
    try:
        logged_in = 'user_id' in session
        user_name = session.get('user_name', '')
        user_picture = session.get('user_picture', '')
        
        recent_music_list = []
        popular_music_list = []
        
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                
                # 최신 음악 데이터 가져오기
                recent_response = requests.get(
                    f'{BACKEND_API_URL}/playlist',
                    headers=headers,
                    timeout=10
                )
                
                # 인기 음악 데이터 가져오기  
                popular_response = requests.get(
                    f'{BACKEND_API_URL}/popular-playlist',
                    headers=headers,
                    timeout=10
                )
                
                # 최신 음악 데이터 처리
                if recent_response.status_code == 200:
                    recent_result = recent_response.json()
                    if recent_result.get('success'):
                        recent_data = recent_result.get('data', {})
                        recent_music_list = recent_data.get('musicList', [])
                        print(f"✅ 백엔드에서 최신 음악 {len(recent_music_list)}개 로드 성공")
                
                # 인기 음악 데이터 처리
                if popular_response.status_code == 200:
                    popular_result = popular_response.json()
                    if popular_result.get('success'):
                        popular_data = popular_result.get('data', {})
                        popular_music_list = popular_data.get('musicList', [])
                        print(f"✅ 백엔드에서 인기 음악 {len(popular_music_list)}개 로드 성공")
                        
            except requests.RequestException as e:
                print(f"백엔드 API 요청 오류: {e}")
            except Exception as e:
                print(f"백엔드 데이터 처리 오류: {e}")
        
        # 백엔드 연결 실패 시 빈 리스트 사용
        if not recent_music_list and not popular_music_list:
            print("⚠️ 백엔드 서버에 연결할 수 없습니다.")

        return render_template('playlist_main.html',
                            logged_in=logged_in,
                            user_name=user_name,
                            user_picture=user_picture,
                            recent_music_list=recent_music_list,
                            popular_music_list=popular_music_list)
                            
    except Exception as e:
        print(f"플레이리스트 메인 페이지 오류: {e}")
        # 오류 발생 시 빈 리스트로 페이지 렌더링
        return render_template('playlist_main.html',
                            logged_in=False,
                            user_name='',
                            user_picture='',
                            recent_music_list=[],
                            popular_music_list=[])


@app.route('/generation-complete')
def generation_complete():
    """음악 생성 완료 페이지"""
    music_id = request.args.get('music_id', '')
    return render_template('generation_complete.html', music_id=music_id)


@app.route('/upload', methods=['POST'])
def upload_file():
    """음악 파일 업로드 처리"""
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({'success': True, 'filename': filename})

    return jsonify({'error': '허용되지 않는 파일 형식입니다'}), 400


@app.route('/image-create')
def image_create():
    logged_in = 'user_id' in session
    user_name = session.get('user_name', '')
    user_picture = session.get('user_picture', '')

    return render_template('image_create.html',
                           logged_in=logged_in,
                           user_name=user_name,
                           user_picture=user_picture)


@app.route('/detail-input')
def detail_input():
    music_id = request.args.get('music_id', '')
    logged_in = 'user_id' in session
    user_name = session.get('user_name', '')
    user_picture = session.get('user_picture', '')

    return render_template('detail_input.html',
                           music_id=music_id,
                           logged_in=logged_in,
                           user_name=user_name,
                           user_picture=user_picture)


@app.route('/play/<music_id>')
def play_music(music_id):
    """음악 재생 데이터 반환"""
    return jsonify({
        'success': True,
        'url': url_for('static', filename='music/demo.mp3')
    })


@app.route('/download/<music_id>')
def download_music(music_id):
    """음악 다운로드"""
    return send_from_directory(
        app.config['MUSIC_FOLDER'],
        'demo.mp3',
        as_attachment=True,
        download_name=f"music_{music_id}.mp3"
    )


@app.route('/delete/<music_id>', methods=['DELETE'])
def delete_music(music_id):
    """음악 삭제 - 백엔드 API 호출"""
    try:
        # 로그인 상태 확인
        if not is_user_logged_in():
            return jsonify({
                'success': False,
                'error': '로그인이 필요합니다.'
            }), 401

        # 백엔드 API 호출 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                
                response = requests.delete(
                    f'{BACKEND_API_URL}/music/{music_id}',
                    headers=headers,
                    timeout=10
                )
                
                print(f"백엔드 삭제 응답: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"✓ 백엔드에서 음악 삭제 성공: 음악 ID {music_id}")
                        return jsonify({
                            'success': True,
                            'message': '음악이 삭제되었습니다.'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': result.get('message', '음악 삭제에 실패했습니다.')
                        }), 400
                elif response.status_code == 401:
                    return jsonify({
                        'success': False,
                        'error': '인증이 필요합니다.'
                    }), 401
                elif response.status_code == 403:
                    return jsonify({
                        'success': False,
                        'error': '이 음악을 삭제할 권한이 없습니다.'
                    }), 403
                elif response.status_code == 404:
                    return jsonify({
                        'success': False,
                        'error': '삭제할 음악을 찾을 수 없습니다.'
                    }), 404
                else:
                    return jsonify({
                        'success': False,
                        'error': f'서버 오류: {response.status_code}'
                    }), response.status_code
                    
            except requests.RequestException as e:
                print(f"백엔드 삭제 요청 오류: {e}")
                # 백엔드 실패 시 로컬 처리로 fallback

        # 로컬 처리 (백엔드 연결 실패 시)
        print("백엔드 연결 실패. 로컬 삭제 처리를 시도합니다.")
        music_list = load_music_data()
        
        for i, music in enumerate(music_list):
            if music['id'] == music_id:
                if 'user_id' in session and music['user_id'] != session['user_id']:
                    return jsonify({
                        'success': False,
                        'error': '이 음악을 삭제할 권한이 없습니다.'
                    }), 403

                del music_list[i]
                save_music_data(music_list)
                print(f"✓ 로컬에서 음악 삭제 성공: 음악 ID {music_id}")
                return jsonify({
                    'success': True,
                    'message': '음악이 삭제되었습니다.'
                })

        return jsonify({
            'success': False,
            'error': '음악을 찾을 수 없습니다.'
        }), 404

    except Exception as e:
        print(f"음악 삭제 오류: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    """구글 로그인 처리"""
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        google_login_url = get_google_login_url()
        if google_login_url:
            return redirect(google_login_url)
        else:
            return render_template('login.html', error="Google 인증 서버에 연결할 수 없습니다.")

    return render_template('login.html')


@app.route('/auth/google/callback')
def login_callback():
    """Google OAuth 콜백 처리"""
    success, error_message = handle_google_callback()

    if success:
        return redirect(url_for('index'))
    else:
        return render_template('login.html', error=error_message)


@app.route('/logout')
def logout():
    """로그아웃 처리"""
    session.clear()
    return redirect(url_for('index'))


@app.context_processor
def inject_user():
    return {
        'logged_in': session.get('logged_in', False),
        'user_name': session.get('user_name', ''),
        'user_picture': session.get('user_picture', ''),
        'user_email': session.get('user_email', '')
    }


@app.route('/debug/session')
def debug_session():
    """세션 상태 디버깅"""
    session_info = {
        'logged_in': session.get('logged_in'),
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'access_token_exists': bool(session.get('access_token')),
        'jwt_token_exists': bool(session.get('jwt_token')),
        'access_token_preview': session.get('access_token', '')[:20] + '...' if session.get('access_token') else None,
        'jwt_token_preview': session.get('jwt_token', '')[:20] + '...' if session.get('jwt_token') else None,
        'all_session_keys': list(session.keys())
    }
    return jsonify(session_info)


@app.route('/debug/backend-test')
def debug_backend_test():
    """백엔드 연결 테스트"""
    try:
        # 1. Health check
        health_response = requests.get(f'{BACKEND_API_URL}/health', timeout=5)

        # 2. 토큰 있을 때와 없을 때 playlist 요청 테스트
        headers_without_token = {'Content-Type': 'application/json'}
        playlist_without_token = requests.get(f'{BACKEND_API_URL}/playlist', headers=headers_without_token, timeout=5)

        headers_with_token = get_auth_headers()
        playlist_with_token = requests.get(f'{BACKEND_API_URL}/playlist', headers=headers_with_token, timeout=5)

        return jsonify({
            'health_check': {
                'status': health_response.status_code,
                'response': health_response.json() if health_response.status_code == 200 else health_response.text
            },
            'playlist_without_token': {
                'status': playlist_without_token.status_code,
                'response': playlist_without_token.json() if playlist_without_token.status_code == 200 else playlist_without_token.text
            },
            'playlist_with_token': {
                'status': playlist_with_token.status_code,
                'response': playlist_with_token.json() if playlist_with_token.status_code == 200 else playlist_with_token.text,
                'headers_sent': headers_with_token
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/music/<int:music_id>/like', methods=['POST'])
def like_music(music_id):
    """음악 좋아요 추가"""
    try:
        # 로그인 확인
        if not is_user_logged_in():
            return jsonify({
                'success': False,
                'message': '로그인이 필요합니다.'
            }), 401
        
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                response = requests.post(
                    f'{BACKEND_API_URL}/music/{music_id}/like',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return jsonify(result)
                else:
                    result = response.json()
                    return jsonify(result), response.status_code
                    
            except requests.RequestException as e:
                print(f"백엔드 좋아요 요청 오류: {e}")
        
        # 백엔드 연결 실패 시 오류 반환
        return jsonify({
            'success': False,
            'message': '백엔드 서버에 연결할 수 없습니다.'
        }), 503
        
    except Exception as e:
        print(f"좋아요 추가 오류: {e}")
        return jsonify({
            'success': False,
            'message': '좋아요 처리 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/music/<int:music_id>/like', methods=['DELETE'])
def unlike_music(music_id):
    """음악 좋아요 취소"""
    try:
        # 로그인 확인
        if not is_user_logged_in():
            return jsonify({
                'success': False,
                'message': '로그인이 필요합니다.'
            }), 401
        
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                response = requests.delete(
                    f'{BACKEND_API_URL}/music/{music_id}/like',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return jsonify(result)
                else:
                    result = response.json()
                    return jsonify(result), response.status_code
                    
            except requests.RequestException as e:
                print(f"백엔드 좋아요 취소 요청 오류: {e}")
        
        # 백엔드 연결 실패 시 오류 반환
        return jsonify({
            'success': False,
            'message': '백엔드 서버에 연결할 수 없습니다.'
        }), 503
        
    except Exception as e:
        print(f"좋아요 취소 오류: {e}")
        return jsonify({
            'success': False,
            'message': '좋아요 취소 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/playlist', methods=['GET'])
def api_get_playlist():
    """API - 전체 플레이리스트 조회"""
    try:
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                response = requests.get(
                    f'{BACKEND_API_URL}/playlist',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    print(f"백엔드 플레이리스트 오류: {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"백엔드 플레이리스트 요청 오류: {e}")
        
        # 백엔드 연결 실패 시 오류 반환
        return jsonify({
            'success': False,
            'message': '백엔드 서버에 연결할 수 없습니다.'
        }), 503
        
    except Exception as e:
        print(f"API 플레이리스트 오류: {e}")
        return jsonify({
            'success': False,
            'message': '플레이리스트 조회 중 오류가 발생했습니다.'
        }), 500


@app.route('/api/popular-playlist', methods=['GET'])
def api_get_popular_playlist():
    """API - 인기 플레이리스트 조회"""
    try:
        # 백엔드 연결 시도
        if check_backend_connection():
            try:
                headers = get_auth_headers()
                response = requests.get(
                    f'{BACKEND_API_URL}/popular-playlist',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    print(f"백엔드 인기 플레이리스트 오류: {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"백엔드 인기 플레이리스트 요청 오류: {e}")
        
        # 백엔드 연결 실패 시 오류 반환
        return jsonify({
            'success': False,
            'message': '백엔드 서버에 연결할 수 없습니다.'
        }), 503
        
    except Exception as e:
        print(f"API 인기 플레이리스트 오류: {e}")
        return jsonify({
            'success': False,
            'message': '인기 플레이리스트 조회 중 오류가 발생했습니다.'
        }), 500


if __name__ == '__main__':
    app.run(debug=True)