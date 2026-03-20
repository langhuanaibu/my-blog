// 平滑滚动导航
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有导航链接
    const navLinks = document.querySelectorAll('.nav-link');
    
    // 为每个导航链接添加点击事件监听
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 获取目标URL
            const targetUrl = this.getAttribute('href');
            
            // 只对页面内锚点应用平滑滚动
            if (targetUrl.startsWith('#')) {
                e.preventDefault();
                
                // 获取目标ID
                const targetElement = document.querySelector(targetUrl);
                
                // 计算滚动位置（考虑固定头部的高度）
                const headerHeight = document.querySelector('.header').offsetHeight;
                const targetPosition = targetElement.offsetTop - headerHeight;
                
                // 平滑滚动
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
            // 对于指向外部页面的链接，保持默认跳转行为
        });
    });
    
    // 表单提交处理
    const contactForm = document.querySelector('.contact-form');
    
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // 这里可以添加表单验证和提交逻辑
            alert('留言已发送，感谢您的支持！');
            
            // 重置表单
            this.reset();
        });
    }
    
    // 滚动时导航栏样式变化
    window.addEventListener('scroll', function() {
        const header = document.querySelector('.header');
        
        if (window.scrollY > 100) {
            header.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
            header.style.backdropFilter = 'blur(10px)';
        } else {
            header.style.backgroundColor = '#fff';
            header.style.backdropFilter = 'none';
        }
    });
    
    // 文章卡片悬停效果增强
    const blogCards = document.querySelectorAll('.blog-card');
    
    blogCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // 页面加载动画
    const sections = document.querySelectorAll('section');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(30px)';
        section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(section);
    });
});