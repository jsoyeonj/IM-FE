// 음악 생성 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 템포 슬라이더 설정
    const tempoSlider = document.getElementById('tempoSlider');
    const tempoValue = document.getElementById('tempoValue');
    const createMusicBtn = document.getElementById('createMusicBtn');
    const musicList = document.getElementById('musicList');

    // 초기 값 설정
    tempoValue.textContent = `${tempoSlider.value} BPM`;

    // 슬라이더 이벤트 리스너
    tempoSlider.addEventListener('input', function() {
        tempoValue.textContent = `${this.value} BPM`;
    });

    // 음악 생성 버튼 이벤트 리스너
    createMusicBtn.addEventListener('click', function() {
        const tempo = tempoSlider.value;
        this.disabled = true;
        this.textContent = '생성 중...';
        this.classList.add('create-button-after');

        // 서버에 음악 생성 요청 보내기 (AJAX)
        fetch('/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tempo: tempo })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 생성된 음악을 목록에 추가
                addMusicToList(data.music);
                showSuccessMessage('음악이 생성되었습니다!');
            } else {
                showErrorMessage(data.error || '음악 생성 중 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorMessage('서버 연결 오류가 발생했습니다.');
        })
        .finally(() => {
            // 버튼 상태 복원
            createMusicBtn.disabled = false;
            createMusicBtn.textContent = '생성';
            createMusicBtn.classList.remove('create-button-after');
        });
    });

    // 음악 목록에 새 항목 추가 함수
    function addMusicToList(music) {
        const musicItem = document.createElement('div');
        musicItem.className = 'music-container';
        musicItem.dataset.id = music.id;

        musicItem.innerHTML = `
            <div class="column-box">
                <h3>${music.title || '제목 없음'}</h3>
                <p>BPM: ${music.tempo}</p>
                <p>생성일: ${formatDate(music.created_at)}</p>
            </div>
            <div class="music-controls">
                <button class="play-btn" onclick="playMusic('${music.id}')">
                    <img src="/static/images/play.png" alt="재생" width="24">
                </button>
                <button class="download-btn" onclick="downloadMusic('${music.id}')">
                    <img src="/static/images/download.png" alt="다운로드" width="24">
                </button>
                <button class="delete-btn" onclick="deleteMusic('${music.id}')">
                    <img src="/static/images/delete.png" alt="삭제" width="24">
                </button>
            </div>
        `;

        musicList.prepend(musicItem); // 새 항목을 목록 맨 위에 추가
    }

    // 날짜 포맷팅 함수
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // 성공 메시지 표시 함수
    function showSuccessMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message success';
        messageDiv.textContent = message;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.classList.add('show');
        }, 10);

        setTimeout(() => {
            messageDiv.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(messageDiv);
            }, 300);
        }, 3000);
    }

    // 오류 메시지 표시 함수
    function showErrorMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message error';
        messageDiv.textContent = message;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.classList.add('show');
        }, 10);

        setTimeout(() => {
            messageDiv.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(messageDiv);
            }, 300);
        }, 3000);
    }
});

// 음악 재생 함수
function playMusic(musicId) {
    fetch(`/play/${musicId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const audio = new Audio(data.url);
            audio.play();
        } else {
            console.error('음악 재생 오류:', data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}

// 음악 다운로드 함수
function downloadMusic(musicId) {
    window.location.href = `/download/${musicId}`;
}

// 음악 삭제 함수
function deleteMusic(musicId) {
    if (confirm('정말로 이 음악을 삭제하시겠습니까?')) {
        fetch(`/delete/${musicId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 목록에서 삭제된 항목 제거
                const musicItem = document.querySelector(`.music-container[data-id="${musicId}"]`);
                if (musicItem) {
                    musicItem.remove();
                }
                showSuccessMessage('음악이 삭제되었습니다.');
            } else {
                showErrorMessage(data.error || '음악 삭제 중 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorMessage('서버 연결 오류가 발생했습니다.');
        });
    }
}