document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const imageUploadArea = document.querySelector('.image-upload-area');
    const uploadContent = document.querySelector('.upload-content');
    const uploadText = document.querySelector('.upload-text');
    const playBtn = document.getElementById('playBtn');
    const recordImg = document.querySelector('.record-img');

    // URL 파라미터로 모드 확인
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode') || 'image'; // 기본값은 이미지 모드

    // 상태 관리
    let isPlaying = false;
    let recordRotation = null;
    let selectedFile = null;

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

    // 파일 업로드 영역 클릭 시 파일 선택 다이얼로그 열기
    if (imageUploadArea) {
        imageUploadArea.addEventListener('click', function(e) {
            // 파일이 업로드된 상태가 아닐 때만 파일 선택 창 열기
            if (!selectedFile && e.target !== fileInput) {
                fileInput.click();
            }
            // 파일이 업로드된 상태일 때는 음악 생성 로직 실행
            else if (selectedFile && imageUploadArea.classList.contains('uploaded')) {
                e.preventDefault(); // 파일 선택 창 열리는 것 방지

                // 음악 생성 로직
                const uploadText = document.querySelector('.upload-text.uploaded');
                if (uploadText) {
                    const fileTypeText = mode === 'video' ? '동영상' : '사진';
                    uploadText.textContent = '생성 중...';
                }
                imageUploadArea.style.pointerEvents = 'none';

                // FormData 생성
                const formData = new FormData();
                const fieldName = mode === 'video' ? 'video' : 'image';
                formData.append(fieldName, selectedFile);

                // 서버 엔드포인트 결정
                const endpoint = mode === 'video' ? '/generate-music-from-video' : '/generate-music-from-image';

                // 서버에 데이터 전송
                fetch(endpoint, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const fileTypeText = mode === 'video' ? '동영상' : '이미지';
                        showMessage(`${fileTypeText}로부터 음악이 생성되었습니다!`, 'success');
                        // 생성 완료 페이지로 리다이렉트
                        setTimeout(() => {
                            window.location.href = data.redirect_url;
                        }, 1000);
                    } else {
                        showMessage(data.error || '음악 생성 중 오류가 발생했습니다', 'error');
                        // 버튼 상태 복원
                        if (uploadText) {
                            const fileTypeText = mode === 'video' ? '동영상으로 음악 생성하기' : '사진으로 음악 생성하기';
                            uploadText.textContent = fileTypeText;
                        }
                        imageUploadArea.style.pointerEvents = 'auto';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showMessage('서버 연결 오류가 발생했습니다', 'error');
                    // 버튼 상태 복원
                    if (uploadText) {
                        const fileTypeText = mode === 'video' ? '동영상으로 음악 생성하기' : '사진으로 음악 생성하기';
                        uploadText.textContent = fileTypeText;
                    }
                    imageUploadArea.style.pointerEvents = 'auto';
                });
            }
        });
    }

    // 파일 업로드 시 처리
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                const fileType = selectedFile.type;

                // 파일 타입 검증
                if (mode === 'video' && !fileType.startsWith('video/')) {
                    showMessage('동영상 파일만 업로드 가능합니다', 'error');
                    return;
                } else if (mode === 'image' && !fileType.startsWith('image/')) {
                    showMessage('이미지 파일만 업로드 가능합니다', 'error');
                    return;
                }

                // 미리보기 표시
                const reader = new FileReader();
                reader.onload = function(event) {
                    // 기존 미리보기 초기화
                    filePreview.innerHTML = '';

                    // 업로드 영역 변경
                    imageUploadArea.classList.add('uploaded');
                    uploadContent.classList.add('uploaded');

                    // 파일 타입에 따른 미리보기 생성
                    let previewHTML = '';
                    if (mode === 'video') {
                        previewHTML = `
                            <div class="preview-content">
                                <div class="preview-img-container">
                                    <video controls class="preview-img" style="max-width: 150px; max-height: 4rem;">
                                        <source src="${event.target.result}" type="${fileType}">
                                        동영상을 재생할 수 없습니다.
                                    </video>
                                </div>
                                <span class="upload-text uploaded">동영상으로 음악 생성하기</span>
                            </div>
                        `;
                    } else {
                        previewHTML = `
                            <div class="preview-content">
                                <div class="preview-img-container">
                                    <img src="${event.target.result}" alt="업로드된 이미지" class="preview-img">
                                </div>
                                <span class="upload-text uploaded">사진으로 음악 생성하기</span>
                            </div>
                        `;
                    }

                    uploadContent.innerHTML = previewHTML;
                };

                reader.readAsDataURL(selectedFile);

                // 성공 메시지 표시
                const fileTypeText = mode === 'video' ? '동영상' : '사진';
                showMessage(`${fileTypeText}이 성공적으로 업로드되었습니다!`, 'success');
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