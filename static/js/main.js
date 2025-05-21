// 페이지가 로드되었을 때 실행되는 코드
document.addEventListener('DOMContentLoaded', function() {
    console.log('Croffle 애플리케이션이 시작되었습니다');

    // 버튼 호버 효과
    const buttons = document.querySelectorAll('.start-button, .login-button');

    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
            this.style.transition = 'transform 0.3s';
        });

        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
});

// 애니메이션 및 기타 시각적 효과를 위한 헬퍼 함수들
const animations = {
    fadeIn: function(element, duration = 500) {
        element.style.opacity = 0;
        element.style.transition = `opacity ${duration}ms`;

        setTimeout(() => {
            element.style.opacity = 1;
        }, 10);
    },

    slideIn: function(element, direction = 'right', duration = 500) {
        let startPos;

        switch(direction) {
            case 'right':
                startPos = 'translateX(50px)';
                break;
            case 'left':
                startPos = 'translateX(-50px)';
                break;
            case 'top':
                startPos = 'translateY(-50px)';
                break;
            case 'bottom':
                startPos = 'translateY(50px)';
                break;
        }

        element.style.transform = startPos;
        element.style.opacity = 0;
        element.style.transition = `transform ${duration}ms, opacity ${duration}ms`;

        setTimeout(() => {
            element.style.transform = 'translate(0)';
            element.style.opacity = 1;
        }, 10);
    }
};

// 페이지 로드 시 애니메이션 적용
document.addEventListener('DOMContentLoaded', function() {
    const mainTitle = document.querySelector('.main-title');
    const subTitle = document.querySelector('.sub-title');
    const startButton = document.querySelector('.start-button');
    const loginButton = document.querySelector('.login-button');

    if (mainTitle) animations.fadeIn(mainTitle, 800);
    if (subTitle) {
        setTimeout(() => {
            animations.fadeIn(subTitle, 800);
        }, 400);
    }

    if (startButton) {
        setTimeout(() => {
            animations.slideIn(startButton, 'bottom', 800);
        }, 800);
    }

    if (loginButton) {
        setTimeout(() => {
            animations.slideIn(loginButton, 'bottom', 800);
        }, 1200);
    }
});