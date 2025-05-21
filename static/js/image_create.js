document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const imageUploadArea = document.querySelector('.image-upload-area');
    const uploadContent = document.querySelector('.upload-content');
    const uploadText = document.querySelector('.upload-text');
    const playBtn = document.getElementById('playBtn');
    const recordImg = document.querySelector('.record-img');

    // 상태 관리
    let isPlaying = false;
    let recordRotation = null;
    let selectedImage = null;

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

    // 이미지 업로드 영역 클릭 시 파일 선택 다이얼로그 열기
    if (imageUploadArea) {
        imageUploadArea.addEventListener('click', function(e) {
            // input 요소가 클릭된 경우는 중복 실행 방지
            if (e.target !== imageInput) {
                imageInput.click();
            }
        });
    }

    // 이미지 업로드 시 처리
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                selectedImage = e.target.files[0];

                // 미리보기 표시
                const reader = new FileReader();
                reader.onload = function(event) {
                    // 기존 미리보기 초기화
                    imagePreview.innerHTML = '';

                    // 업로드 영역 변경
                    imageUploadArea.classList.add('uploaded');
                    uploadContent.classList.add('uploaded');

                    // 업로드된 이미지와 텍스트를 포함한 새 컨텐츠 생성
                    uploadContent.innerHTML = `
                        <div class="preview-content">
                            <div class="preview-img-container">
                                <img src="${event.target.result}" alt="업로드된 이미지" class="preview-img">
                            </div>
                            <span class="upload-text uploaded">사진으로 음악 생성하기</span>
                        </div>
                    `;
                };

                reader.readAsDataURL(selectedImage);

                // "사진이 성공적으로 업로드되었습니다!" 메시지 표시
                showMessage('사진이 성공적으로 업로드되었습니다!', 'success');
            }
        });
    }

    // 이미지 업로드 버튼이 변형된 후 클릭 시 (이미지가 이미 선택된 상태)
    if (imageUploadArea) {
        imageUploadArea.addEventListener('click', function(e) {
            // 이미지가 선택되었고, 파일 input이 클릭되지 않은 경우
            if (selectedImage && e.target !== imageInput) {
                // 클래스가 업로드된 상태일 때만 처리
                if (imageUploadArea.classList.contains('uploaded')) {
                    // 음악 생성 로직
                    const uploadText = document.querySelector('.upload-text.uploaded');
                    if (uploadText) {
                        uploadText.textContent = '생성 중...';
                    }
                    imageUploadArea.style.pointerEvents = 'none';

                    // FormData 생성
                    const formData = new FormData();
                    formData.append('image', selectedImage);

                    // 서버에 데이터 전송
                    fetch('/generate-music-from-image', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showMessage('이미지로부터 음악이 생성되었습니다!', 'success');
                            // 일정 시간 후 플레이리스트 페이지로 리다이렉트
                            setTimeout(() => {
                                window.location.href = `/playlist?music_id=${data.music_id}`;
                            }, 1500);
                        } else {
                            showMessage(data.error || '음악 생성 중 오류가 발생했습니다', 'error');
                            // 버튼 상태 복원
                            if (uploadText) {
                                uploadText.textContent = '사진으로 음악 생성하기';
                            }
                            imageUploadArea.style.pointerEvents = 'auto';
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showMessage('서버 연결 오류가 발생했습니다', 'error');
                        // 버튼 상태 복원
                        if (uploadText) {
                            uploadText.textContent = '사진으로 음악 생성하기';
                        }
                        imageUploadArea.style.pointerEvents = 'auto';
                    });
                }
            }
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