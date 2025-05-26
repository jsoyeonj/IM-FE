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


@app.route('/generate-music', methods=['POST'])
def generate_music():
    """텍스트 기반 음악 생성 - 로그인 상태 확인 추가"""
    try:
        data = request.get_json()
        print(f"음악 생성 요청 데이터: {data}")
        print(f"환경변수 BACKEND_API_URL: {BACKEND_API_URL}")

        # 로그인 상태 확인
        user_logged_in = is_user_logged_in()
        print(f"👤 사용자 로그인 상태: {user_logged_in}")

        # 필수 파라미터 확인
        if not data or 'mood' not in data or 'location' not in data:
            return jsonify({
                'success': False,
                'error': '분위기와 장소 정보가 필요합니다.'
            }), 400

        # 백엔드 연결 확인
        backend_connected = check_backend_connection()
        print(f"백엔드 연결 상태: {backend_connected}")

        if backend_connected:
            # 백엔드 API 호출 시도
            try:
                prompt1 = f"{data['mood']} 분위기의 {data['location']} 음악, 템포 {data.get('speed', 50)}"

                api_data = {
                    'prompt1': prompt1
                }

                print(f"백엔드로 전송할 데이터: {api_data}")
                print(f"요청 URL: {BACKEND_API_URL}/generate-music")

                # 인증 헤더 포함
                headers = get_auth_headers()
                print(f"요청 헤더: {headers}")

                response = requests.post(
                    f'{BACKEND_API_URL}/generate-music',
                    json=api_data,
                    headers=headers,
                    timeout=30
                )

                print(f"백엔드 응답 상태: {response.status_code}")
                print(f"백엔드 응답 내용: {response.text}")

                if response.status_code == 200:
                    result = response.json()
                    print(f"백엔드 응답 파싱: {result}")

                    if result.get('success'):
                        music_data = result.get('data', {})
                        music_url = music_data.get('musicUrl')
                        title = music_data.get('title')
                        music_id = str(uuid.uuid4())

                        if user_logged_in:
                            print(f"✓ 로그인된 사용자: 백엔드에서 music_tb + mymusic_tb에 저장됨")
                        else:
                            print(f"✓ 익명 사용자: 백엔드에서 music_tb에만 저장됨")

                        print(f"✓ 백엔드에서 음악 생성 성공: {title}")

                        return jsonify({
                            'success': True,
                            'music_id': music_id,
                            'music_url': music_url,
                            'title': title,
                            'next_step': url_for('detail_input', music_id=music_id)
                        })
                    else:
                        print(f"백엔드 응답 실패: {result.get('message', '알 수 없는 오류')}")
                elif response.status_code == 401:
                    print("❌ 인증 실패: JWT 토큰이 유효하지 않습니다.")
                else:
                    print(f"백엔드 HTTP 오류: {response.status_code} - {response.text}")
            except requests.RequestException as e:
                print(f"백엔드 요청 예외: {e}")
            except Exception as e:
                print(f"백엔드 처리 예외: {e}")

        # 백엔드 연결 실패 시 로컬 처리
        print("⚠️ 백엔드 서버에 연결할 수 없거나 음악 생성에 실패했습니다. 로컬 모드로 실행합니다.")

        music_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()

        # 로컬 음악 정보 생성
        music_data = {
            'id': music_id,
            'title': f'{data["mood"]} 분위기의 {data["location"]} 음악',
            'speed': data['speed'],
            'mood': data['mood'],
            'location': data['location'],
            'created_at': created_at,
            'file_path': f'{music_id}.mp3',
            'user_id': session.get('user_id', 'anonymous')
        }

        # 로컬 음악 데이터에 추가
        all_music = load_music_data()
        all_music.append(music_data)
        save_music_data(all_music)

        print(f"✓ 로컬에 음악 데이터 저장: {music_data['title']}")

        return jsonify({
            'success': True,
            'music_id': music_id,
            'next_step': url_for('detail_input', music_id=music_id)
        })

    except Exception as e:
        print(f"음악 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }), 500


@app.route('/generate-music-with-detail', methods=['POST'])
def generate_music_with_detail():
    """상세 내용을 반영한 음악 생성"""
    try:
        data = request.get_json()

        if 'detail_text' not in data:
            return jsonify({
                'success': False,
                'error': '상세 내용이 필요합니다'
            }), 400

        detail_text = data.get('detail_text')
        music_id = data.get('music_id', '')

        # 백엔드 연결 확인 및 시도
        if check_backend_connection():
            try:
                # prompt2 제거
                api_data = {
                    'prompt1': detail_text
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

                        print(f"✓ 백엔드에서 상세 음악 생성 성공: {music_data.get('title')}")

                        return jsonify({
                            'success': True,
                            'music_id': new_music_id,
                            'music_url': music_data.get('musicUrl'),
                            'title': music_data.get('title'),
                            'redirect_url': url_for('generation_complete', music_id=new_music_id)
                        })
                else:
                    print(f"백엔드 상세 음악 생성 오류: {response.status_code} - {response.text}")
            except requests.RequestException:
                pass

        # 로컬 처리
        if not music_id:
            music_id = str(uuid.uuid4())

        created_at = datetime.datetime.now().isoformat()

        new_music_data = {
            'id': music_id,
            'title': f"{detail_text[:20]}{'...' if len(detail_text) > 20 else ''}",
            'detail_text': detail_text,
            'created_at': created_at,
            'file_path': f'{music_id}.mp3',
            'user_id': session.get('user_id', 'anonymous')
        }

        music_list = load_music_data()

        if music_id and any(music['id'] == music_id for music in music_list):
            for i, music in enumerate(music_list):
                if music['id'] == music_id:
                    music_list[i].update(new_music_data)
                    break
        else:
            music_list.append(new_music_data)

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


@app.route('/generation-complete')
def generation_complete():
    """음악 생성 완료 페이지"""
    music_id = request.args.get('music_id', '')
    return render_template('generation_complete.html', music_id=music_id)


# 나머지 라우트들은 기존과 동일...
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
    """음악 삭제"""
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
            return jsonify({'success': True})

    return jsonify({
        'success': False,
        'error': '음악을 찾을 수 없습니다.'
    }), 404


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


# app.py에 추가할 디버깅 라우트

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


if __name__ == '__main__':
    app.run(debug=True)
.