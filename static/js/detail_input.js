document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const detailInput = document.getElementById('detailInput');
    const generateBtn = document.getElementById('generateBtn');
    const playBtn = document.getElementById('playBtn');
    const recordImg = document.querySelector('.record-img');

    // 파라미터 가져오기
    const urlParams = new URLSearchParams(window.location.search);
    const musicId = urlParams.get('music_id');

    // 상태 관리
    let isPlaying = false;
    let recordRotation = null;

    // 레코드 회전 애니메이션 함수
    function startRecordRotation() {
        if (recordRotation) return; // 이미 회전 중이면 중복 실행 방지

        let degree = 0;
        recordRotation = setInterval(() => {
            degree += 1;
            if (recordImg) {
                recordImg.style.transform = `rotate(${degree}deg)`;
            }
        }, 30);
    }

    function stopRecordRotation() {
        if (recordRotation) {
            clearInterval(recordRotation);
            recordRotation = null;

            // 회전 효과 초기화
            if (recordImg) {
                // 현재 각도 저장
                const currentTransform = window.getComputedStyle(recordImg).getPropertyValue('transform');
                const matrix = new DOMMatrix(currentTransform);
                const angle = Math.atan2(matrix.b, matrix.a) * (180 / Math.PI);

                // transition 일시적으로 제거하고 현재 각도로 설정
                recordImg.style.transition = 'none';
                recordImg.style.transform = `rotate(${angle}deg)`;

                // 리플로우 강제
                void recordImg.offsetWidth;

                // transition 다시 설정
                recordImg.style.transition = 'transform 2s ease-in-out';
            }
        }
    }

    // 레코드 재생/일시정지 기능
    if (playBtn) {
        playBtn.addEventListener('click', function() {
            if (isPlaying) {
                // 일시정지 상태로 변경
                isPlaying = false;
                this.querySelector('.play-icon').src = '/static/images/playIcon.svg';
                stopRecordRotation();
            } else {
                // 재생 상태로 변경
                isPlaying = true;
                this.querySelector('.play-icon').src = '/static/images/pauseIcon.svg';
                startRecordRotation();
            }
        });
    }

    // 입력 필드 엔터 키 이벤트
    if (detailInput) {
        detailInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                generateBtn.click();
            }
        });
    }

    // 음악 생성 버튼 이벤트
    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            const detailText = detailInput.value.trim();

            if (!detailText) {
                showMessage('원하는 내용을 입력해주세요', 'error');
                return;
            }

            // 버튼 비활성화
            this.disabled = true;
            this.textContent = '생성 중...';

            // 서버에 데이터 전송
            fetch('/generate-music-with-detail', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    music_id: musicId, // 이전 단계에서 생성된 음악 ID (있는 경우)
                    detail_text: detailText
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('음악이 생성되었습니다!', 'success');
                    // 생성 완료 페이지로 리다이렉트
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1000);
                } else {
                    showMessage(data.error || '음악 생성 중 오류가 발생했습니다', 'error');
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.textContent = '음악 생성하기';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('서버 연결 오류가 발생했습니다', 'error');
                // 버튼 상태 복원
                this.disabled = false;
                this.textContent = '음악 생성하기';
            });
        });
    }
});

// 메시지 표시 함수
function showMessage(message, type) {
    // 이미 있는 메시지 제거
    const existingMessage = document.querySelector('.message');
    if (existingMessage) {
        existingMessage.remove();
    }

    // 새 메시지 요소 생성
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;

    // body에 메시지 추가
    document.body.appendChild(messageDiv);

    // 메시지 표시 애니메이션
    setTimeout(() => {
        messageDiv.classList.add('show');
    }, 10);

    // 3초 후 메시지 제거
    setTimeout(() => {
        messageDiv.classList.remove('show');
        setTimeout(() => {
            messageDiv.remove();
        }, 300);
    }, 3000);
}