// 플레이리스트 페이지 JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('플레이리스트 페이지가 로드되었습니다');

    // 각 음악 항목에 호버 효과 추가
    const musicContainers = document.querySelectorAll('.music-container');

    musicContainers.forEach(container => {
        container.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.transition = 'transform 0.3s';
        });

        container.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});

// 음악 재생 함수
function playMusic(musicId) {
    // 현재 재생 중인 음악이 있으면 중지
    const currentPlaying = document.querySelector('.playing');
    if (currentPlaying) {
        currentPlaying.classList.remove('playing');
        const playBtn = currentPlaying.querySelector('.play-btn img');
        playBtn.src = '/static/images/play.png';
    }

    // 상태 표시 업데이트
    const container = document.querySelector(`.music-container[data-id="${musicId}"]`);
    const playBtn = container.querySelector('.play-btn img');

    // 이미 재생 중인 항목을 다시 클릭하면 중지
    if (container.classList.contains('playing')) {
        container.classList.remove('playing');
        playBtn.src = '/static/images/play.png';
        return;
    }

    // 새 음악 재생
    container.classList.add('playing');
    playBtn.src = '/static/images/pause.png';

    fetch(`/play/${musicId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const audio = new Audio(data.url);

            // 오디오 엘리먼트를 전역 변수로 저장하여 나중에 참조할 수 있게 함
            window.currentAudio = audio;

            audio.play();

            // 음악이 끝나면 상태 업데이트
            audio.addEventListener('ended', function() {
                container.classList.remove('playing');
                playBtn.src = '/static/images/play.png';
            });
        } else {
            showErrorMessage(data.error || '음악 재생 중 오류가 발생했습니다.');
            container.classList.remove('playing');
            playBtn.src = '/static/images/play.png';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorMessage('서버 연결 오류가 발생했습니다.');
        container.classList.remove('playing');
        playBtn.src = '/static/images/play.png';
    });
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

                // 목록이 비었는지 확인
                const musicList = document.querySelector('.music-list');
                if (musicList && musicList.children.length === 0) {
                    // 빈 목록 메시지 표시
                    const contentWrapper = document.querySelector('.content-wrapper');
                    const noMusicContainer = document.createElement('div');
                    noMusicContainer.className = 'no-music-container';
                    noMusicContainer.innerHTML = `
                        <p>아직 생성된 작업곡이 없습니다.</p>
                        <a href="/create" class="create-link-button">
                            새 음악 만들기
                        </a>
                    `;

                    // 기존 음악 목록 제거하고 메시지 추가
                    musicList.remove();
                    contentWrapper.appendChild(noMusicContainer);
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