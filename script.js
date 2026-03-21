// 平滑滚动导航
document.addEventListener('DOMContentLoaded', function() {
    // 打字机特效逻辑
    const typewriterElement = document.getElementById('typewriter-text');
    if (typewriterElement) {
        const text = "乌幕屏，海相续，举眼茫茫，静听细浪语";
        let index = 0;
        
        // 创建光标元素
        const cursor = document.createElement('span');
        cursor.className = 'typewriter-cursor';
        cursor.innerHTML = '&nbsp;';
        
        function typeWriter() {
            if (index < text.length) {
                // 每次清空并重新组合文本和光标
                typewriterElement.textContent = text.substring(0, index + 1);
                typewriterElement.appendChild(cursor);
                index++;
                setTimeout(typeWriter, 100); // 打字速度
            }
        }
        
        // 延迟一点开始打字动画
        setTimeout(typeWriter, 500);
    }

    // 主题切换逻辑
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        // 更新按钮图标
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        themeToggle.textContent = currentTheme === 'dark' ? '🌙' : '🌞';

        themeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            if (isDark) {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                themeToggle.textContent = '🌞';
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeToggle.textContent = '🌙';
            }
        });
    }

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
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        
        if (window.scrollY > 100) {
            header.style.backgroundColor = isDark ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)';
            header.style.backdropFilter = 'blur(10px)';
        } else {
            // 恢复使用 CSS 变量，而不是写死颜色
            header.style.backgroundColor = 'var(--header-bg)';
            header.style.backdropFilter = 'none';
        }
    });

    // 监听主题切换，实时更新已经处于滚动状态的导航栏背景色
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const header = document.querySelector('.header');
            if (window.scrollY > 100) {
                // 因为点击按钮后 data-theme 的状态已经被上面的逻辑改变过了，所以这里判断逻辑要取反
                // 如果当前没有 data-theme 属性（意味着刚切回 light），应该显示白色半透明
                // 如果当前有 data-theme='dark'（意味着刚切到 dark），应该显示深色半透明
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                header.style.backgroundColor = isDark ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)';
            } else {
                // 如果在顶部切换主题，确保背景色跟随 CSS 变量
                header.style.backgroundColor = 'var(--header-bg)';
            }
        });
    }
    
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

    // 悬浮菜单逻辑
    const floatingMenu = document.querySelector('.floating-menu');
    const mainBtn = document.getElementById('floating-main-btn');
    const topBtn = document.getElementById('float-top-btn');
    const randomBtn = document.getElementById('float-random-btn');
    const themeBtn = document.getElementById('float-theme-btn');

    if (floatingMenu && mainBtn) {
        // 切换菜单展开/收起
        mainBtn.addEventListener('click', () => {
            floatingMenu.classList.toggle('active');
        });

        // 点击外部关闭菜单
        document.addEventListener('click', (e) => {
            if (!floatingMenu.contains(e.target)) {
                floatingMenu.classList.remove('active');
            }
        });

        // 返回顶部
        if (topBtn) {
            topBtn.addEventListener('click', () => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
                floatingMenu.classList.remove('active');
            });
            
            // 监听滚动显示/隐藏返回顶部按钮
            window.addEventListener('scroll', () => {
                if (window.scrollY > 300) {
                    topBtn.style.display = 'flex';
                } else {
                    topBtn.style.display = 'none';
                }
            });
            // 初始化检查一次
            if (window.scrollY <= 300) topBtn.style.display = 'none';
        }

        // 随机阅读
        if (randomBtn) {
            randomBtn.addEventListener('click', () => {
                // 如果在文章页并且有 blogArticles 数据
                if (typeof blogArticles !== 'undefined' && blogArticles.length > 0) {
                    const randomIndex = Math.floor(Math.random() * blogArticles.length);
                    const randomId = blogArticles[randomIndex].id;
                    
                    // 如果在 articles.html，直接切换内容
                    if (window.location.pathname.includes('articles.html')) {
                        showArticle(randomId);
                        history.pushState(null, null, '#' + randomId);
                    } else {
                        // 否则跳转到 articles.html 并带上 hash
                        window.location.href = 'articles.html#' + randomId;
                    }
                } else {
                    // 如果在首页，跳转到 articles.html
                    window.location.href = 'articles.html';
                }
                floatingMenu.classList.remove('active');
            });
        }

        // 切换主题
        if (themeBtn && themeToggle) {
            // 同步悬浮按钮的图标
            const updateThemeBtnIcon = () => {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                themeBtn.textContent = isDark ? '🌙' : '🌞';
            };
            updateThemeBtnIcon();

            themeBtn.addEventListener('click', () => {
                // 复用原有的主题切换按钮的点击逻辑
                themeToggle.click();
                updateThemeBtnIcon();
                floatingMenu.classList.remove('active');
            });
            
            // 监听原按钮的点击以保持同步
            themeToggle.addEventListener('click', updateThemeBtnIcon);
        }
    }
});