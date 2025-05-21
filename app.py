from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
import datetime
import json
import uuid
import requests
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import secrets

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))  # 세션 관리를 위한 비밀키

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

# 음악 데이터를 저장할 JSON 파일 경로
MUSIC_DATA_FILE = 'music_data.json'

# Google OAuth 도우미 가져오기
from oauth_helper import get_google_login_url, handle_google_callback


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# 날짜 형식 포맷터
@app.template_filter('format_date')
def format_date(value, format='%Y년 %m월 %d일 %H:%M'):
    if isinstance(value, str):
        value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.strftime(format)


# 음악 데이터 로드
def load_music_data():
    if os.path.exists(MUSIC_DATA_FILE):
        with open(MUSIC_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


# 음악 데이터 저장
def save_music_data(data):
    with open(MUSIC_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')


@app.route('/create', methods=['GET', 'POST'])
def create():
    """음악 생성 페이지"""
    if request.method == 'POST':
        data = request.get_json()

        # 필수 파라미터 확인
        required_params = ['tempo', 'mood', 'place']
        missing_params = [param for param in required_params if param not in data]

        if missing_params:
            return jsonify({
                'success': False,
                'error': f"다음 정보가 없습니다: {', '.join(missing_params)}"
            }), 400

        # 음악 생성 시뮬레이션 (실제로는 여기서 음악 생성 API나 알고리즘을 호출)
        # 지금은 더미 데이터로 대체
        music_id = str(uuid.uuid4())
        created_at = datetime.datetime.now().isoformat()

        # 음악 정보 저장
        music_data = {
            'id': music_id,
            'title': f'{data["mood"]} 분위기의 {data["place"]} 음악',
            'tempo': data['tempo'],
            'mood': data['mood'],
            'place': data['place'],
            'created_at': created_at,
            'file_path': f'{music_id}.mp3',
            'user_id': session.get('user_id', 'anonymous')
        }

        # 더미 음악 파일 생성 또는 복사 (실제로는 생성된 음악 파일을 저장)
        # 이 예제에서는 파일이 이미 있다고 가정하고 경로만 저장

        # 음악 데이터 목록에 추가
        all_music = load_music_data()
        all_music.append(music_data)
        save_music_data(all_music)

        return jsonify({
            'success': True,
            'music': music_data
        })

    # GET 요청인 경우 페이지 렌더링
    return render_template('create.html')


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


@app.route('/playlist')
def playlist():
    """사용자의 음악 목록 표시"""
    # 모든 음악 목록 로드
    music_list = load_music_data()

    # 로그인한 사용자의 음악만 필터링 (로그인 상태라면)
    if 'user_id' in session:
        music_list = [music for music in music_list if music['user_id'] == session['user_id']]

    # 생성일 기준 내림차순 정렬
    music_list.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('playlist.html', music_list=music_list)


@app.route('/play/<music_id>')
def play_music(music_id):
    """음악 재생 데이터 반환"""
    music_list = load_music_data()

    # 해당 ID의 음악 찾기
    for music in music_list:
        if music['id'] == music_id:
            # 실제 음악 파일 경로를 반환
            # 이 예제에서는 더미 파일을 사용하고 있으므로 고정 경로 반환
            return jsonify({
                'success': True,
                'url': url_for('static', filename='music/demo.mp3')
            })

    return jsonify({'success': False, 'error': '음악을 찾을 수 없습니다.'}), 404


@app.route('/download/<music_id>')
def download_music(music_id):
    """음악 다운로드"""
    music_list = load_music_data()

    # 해당 ID의 음악 찾기
    for music in music_list:
        if music['id'] == music_id:
            # 실제 파일이 있을 경우 다운로드 제공
            # 이 예제에서는 더미 파일을 제공
            return send_from_directory(
                app.config['MUSIC_FOLDER'],
                'demo.mp3',  # 실제 구현에서는 music['file_path']
                as_attachment=True,
                download_name=f"{music['title']}.mp3"
            )

    return jsonify({'success': False, 'error': '음악을 찾을 수 없습니다.'}), 404


@app.route('/delete/<music_id>', methods=['DELETE'])
def delete_music(music_id):
    """음악 삭제"""
    music_list = load_music_data()

    # 해당 ID의 음악 찾기
    for i, music in enumerate(music_list):
        if music['id'] == music_id:
            # 로그인 상태라면 사용자가 소유한 음악인지 확인
            if 'user_id' in session and music['user_id'] != session['user_id']:
                return jsonify({'success': False, 'error': '이 음악을 삭제할 권한이 없습니다.'}), 403

            # 실제 파일이 있다면 삭제
            file_path = os.path.join(app.config['MUSIC_FOLDER'], music['file_path'])
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"파일 삭제 오류: {e}")

            # 목록에서 제거
            del music_list[i]
            save_music_data(music_list)

            return jsonify({'success': True})

    return jsonify({'success': False, 'error': '음악을 찾을 수 없습니다.'}), 404


@app.route('/login', methods=['GET', 'POST'])
def login():
    """구글 로그인 처리"""
    # 이미 로그인되어 있다면 메인 페이지로 리다이렉트
    if session.get('logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        # 구글 OAuth 로그인 URL 생성
        google_login_url = get_google_login_url()
        if google_login_url:
            return redirect(google_login_url)
        else:
            return render_template('login.html', error="Google 인증 서버에 연결할 수 없습니다.")

    # GET 요청이면 로그인 페이지 표시
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
    # 세션에서 모든 사용자 정보 삭제
    session.clear()
    return redirect(url_for('index'))


# 템플릿에서 사용할 전역 변수
@app.context_processor
def inject_user():
    return {
        'logged_in': session.get('logged_in', False),
        'user_name': session.get('user_name', ''),
        'user_picture': session.get('user_picture', ''),
        'user_email': session.get('user_email', '')
    }


if __name__ == '__main__':
    app.run(debug=True)