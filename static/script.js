function login() {
    const username = document.getElementById('login-username').value.trim();
    
    if (username === '') {
        alert('لطفاً نام کاربری را وارد کنید');
        return;
    }
    
    // ذخیره اسم کاربر
    localStorage.setItem('username', username);
    
    // اگه عکس انتخاب شده بود، ذخیره کن
    const profilePic = document.getElementById('profile-pic').files[0];
    if (profilePic) {
        const reader = new FileReader();
        reader.onload = function(e) {
            localStorage.setItem('profilePic', e.target.result);
        };
        reader.readAsDataURL(profilePic);
    }
    
    // قایم کردن صفحه ورود و نمایش صفحه چت
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('chat-page').style.display = 'block';
    
    // فرستادن اسم کاربر به سرور
    socket.emit('set_username', { username: username });
    
    // نمایش اسم توی هدر چت
    document.querySelector('.chat-header h3').textContent = username;
}
