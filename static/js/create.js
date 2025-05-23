document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const speedSlider = document.getElementById('speedSlider');
    const controllers = document.querySelectorAll('.controller');
    const createButtons = document.querySelectorAll('.create-button');
    const nextStepBtn = document.getElementById('nextStepBtn');
    const playBtn = document.getElementById('playBtn');
    const recordImg = document.querySelector('.record-img');
    const imageGenBtn = document.getElementById('imageGenBtn');
    const videoGenBtn = document.getElementById('videoGenBtn');

    // 선택된 값 관리
    let selectedSpeed = speedSlider ? speedSlider.value : 50;
    let selectedMood = '';
    let selectedPlace = '';
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

    // 스피드 슬라이더 이벤트
    if (speedSlider) {
        speedSlider.addEventListener('input', function() {
            selectedSpeed = this.value;
        });
    }

    // 버튼 클릭 이벤트
    createButtons.forEach(button => {
        button.addEventListener('click', function() {
            const value = this.getAttribute('data-value');
            const controllerLabel = this.closest('.controller').querySelector('.controller-label').innerText;

            // 같은 컨트롤러 내의 다른 버튼들 선택 해제
            const siblingButtons = this.closest('.button-grid').querySelectorAll('.create-button');
            siblingButtons.forEach(btn => btn.classList.remove('selected'));

            // 현재 버튼이 이미 선택된 상태인지 확인
            if ((controllerLabel === '분위기' && selectedMood === value) ||
                (controllerLabel === '장소' && selectedPlace === value)) {
                // 이미 선택된 경우 선택 취소
                this.classList.remove('selected');
                if (controllerLabel === '분위기') selectedMood = '';
                if (controllerLabel === '장소') selectedPlace = '';
            } else {
                // 새로운 선택
                this.classList.add('selected');
                if (controllerLabel === '분위기') selectedMood = value;
                if (controllerLabel === '장소') selectedPlace = value;
            }
        });
    });

    // 다음 단계 버튼 이벤트
    if (nextStepBtn) {
        nextStepBtn.addEventListener('click', function() {
            // 선택 검증
            if (!selectedMood) {
                showMessage('분위기를 선택해주세요', 'error');
                // 분위기 컨트롤러 강조 효과
                highlightController(controllers[1]);
                return;
            }
            if (!selectedPlace) {
                showMessage('장소를 선택해주세요', 'error');
                // 장소 컨트롤러 강조 효과
                highlightController(controllers[2]);
                return;
            }
            // 버튼 비활성화
            this.style.pointerEvents = 'none';
            this.textContent = '생성 중...';
            // 서버에 데이터 전송
            fetch('/generate-music', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    speed: selectedSpeed,
                    mood: selectedMood,
                    location: selectedPlace
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 메시지 표시 및 딜레이 없이 바로 다음 페이지로 이동
                    window.location.href = data.next_step;
                } else {
                    showMessage(data.error || '음악 생성 중 오류가 발생했습니다', 'error');
                    // 버튼 상태 복원
                    this.style.pointerEvents = 'auto';
                    this.textContent = '다음 단계';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('서버 연결 오류가 발생했습니다', 'error');
                // 버튼 상태 복원
                this.style.pointerEvents = 'auto';
                this.textContent = '다음 단계';
            });
        });
    }

    // 이미지로 음악 생성 버튼 이벤트
    if (imageGenBtn) {
        imageGenBtn.addEventListener('click', function() {
            window.location.href = '/image-create';
        });
    }

    // 동영상으로 음악 생성 버튼 이벤트 (동영상 모드로 이미지 생성 페이지로 이동)
    if (videoGenBtn) {
        videoGenBtn.addEventListener('click', function() {
            window.location.href = '/image-create?mode=video';
        });
    }

    // 컨트롤러 강조 효과
    function highlightController(controller) {
        // 현재 transform 효과 저장
        const originalTransform = controller.style.transform;

        // 강조 효과 적용
        controller.style.transform = 'scale(1.1)';
        controller.style.boxShadow = '-3px 8px 20px 3px rgba(0, 0, 0, 0.3)';
        controller.style.zIndex = '10';

        // 잠시 후 원래 상태로 복원
        setTimeout(() => {
            controller.style.transform = originalTransform;
            controller.style.boxShadow = '';
            controller.style.zIndex = '';
        }, 1000);
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