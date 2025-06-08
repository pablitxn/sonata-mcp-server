"""Mock responses for testing various scenarios."""

GOOGLE_SEARCH_RESPONSE = """
<html>
<head><title>python tutorial - Google Search</title></head>
<body>
    <div id="search">
        <div class="g">
            <h3 class="LC20lb">Python Tutorial - W3Schools</h3>
            <a href="https://www.w3schools.com/python/">
                <br>
                <cite>www.w3schools.com › python</cite>
            </a>
            <span class="aCOpRe">
                <span>Well organized and easy to understand Web building tutorials with lots of examples of how to use HTML, CSS, JavaScript, SQL, Python, PHP, Bootstrap, Java...</span>
            </span>
        </div>
        <div class="g">
            <h3 class="LC20lb">The Python Tutorial — Python 3.12 documentation</h3>
            <a href="https://docs.python.org/3/tutorial/">
                <br>
                <cite>docs.python.org › tutorial</cite>
            </a>
            <span class="aCOpRe">
                <span>This tutorial introduces the reader informally to the basic concepts and features of the Python language and system.</span>
            </span>
        </div>
    </div>
</body>
</html>
"""

RECAPTCHA_V2_PAGE = """
<html>
<head>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
</head>
<body>
    <form method="POST">
        <div class="g-recaptcha" 
             data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
             data-callback="onSuccess"
             data-expired-callback="onExpired">
        </div>
        <br/>
        <input type="submit" value="Submit">
    </form>
    <script>
        function onSuccess(token) {
            console.log('reCAPTCHA solved:', token);
        }
        function onExpired() {
            console.log('reCAPTCHA expired');
        }
    </script>
</body>
</html>
"""

OAUTH_LOGIN_PAGE = """
<html>
<head><title>Login with OAuth</title></head>
<body>
    <div class="oauth-container">
        <h1>Sign in to continue</h1>
        <button id="google-login" onclick="loginWithGoogle()">
            Sign in with Google
        </button>
        <button id="github-login" onclick="loginWithGitHub()">
            Sign in with GitHub
        </button>
    </div>
    <script>
        function loginWithGoogle() {
            window.location.href = '/oauth/google/authorize';
        }
        function loginWithGitHub() {
            window.location.href = '/oauth/github/authorize';
        }
    </script>
</body>
</html>
"""

TWO_FACTOR_AUTH_PAGE = """
<html>
<head><title>Two-Factor Authentication</title></head>
<body>
    <form id="2fa-form" method="POST" action="/verify-2fa">
        <h2>Enter verification code</h2>
        <p>Please enter the 6-digit code from your authenticator app</p>
        <input type="text" 
               id="code" 
               name="code" 
               pattern="[0-9]{6}" 
               maxlength="6" 
               required
               autocomplete="off">
        <button type="submit">Verify</button>
        <a href="/2fa/backup">Use backup code instead</a>
    </form>
</body>
</html>
"""

AJAX_CONTENT_PAGE = """
<html>
<head>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                fetch('/api/content')
                    .then(res => res.json())
                    .then(data => {
                        document.getElementById('dynamic-content').innerHTML = data.html;
                    });
            }, 1000);
        });
    </script>
</head>
<body>
    <div id="static-content">
        <h1>Page Title</h1>
        <p>This content is loaded immediately</p>
    </div>
    <div id="dynamic-content">
        <p>Loading...</p>
    </div>
</body>
</html>
"""

INFINITE_SCROLL_PAGE = """
<html>
<head>
    <style>
        .item { height: 100px; margin: 10px; background: #f0f0f0; }
    </style>
</head>
<body>
    <div id="content">
        <div class="item">Item 1</div>
        <div class="item">Item 2</div>
        <div class="item">Item 3</div>
    </div>
    <div id="loading" style="display: none;">Loading more...</div>
    <script>
        let page = 1;
        window.addEventListener('scroll', () => {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 10) {
                loadMore();
            }
        });
        
        function loadMore() {
            document.getElementById('loading').style.display = 'block';
            setTimeout(() => {
                page++;
                for (let i = 1; i <= 3; i++) {
                    const item = document.createElement('div');
                    item.className = 'item';
                    item.textContent = `Item ${page * 3 + i}`;
                    document.getElementById('content').appendChild(item);
                }
                document.getElementById('loading').style.display = 'none';
            }, 500);
        }
    </script>
</body>
</html>
"""

ERROR_RESPONSES = {
    "404": {
        "status_code": 404,
        "content": """
        <html>
        <head><title>404 Not Found</title></head>
        <body>
            <h1>404 - Page Not Found</h1>
            <p>The requested page could not be found.</p>
        </body>
        </html>
        """
    },
    "500": {
        "status_code": 500,
        "content": """
        <html>
        <head><title>500 Internal Server Error</title></head>
        <body>
            <h1>500 - Internal Server Error</h1>
            <p>Something went wrong on our end.</p>
        </body>
        </html>
        """
    },
    "403": {
        "status_code": 403,
        "content": """
        <html>
        <head><title>403 Forbidden</title></head>
        <body>
            <h1>403 - Forbidden</h1>
            <p>You don't have permission to access this resource.</p>
        </body>
        </html>
        """
    }
}

MOCK_API_RESPONSES = {
    "/api/content": {
        "html": "<div><h2>Dynamic Content</h2><p>This was loaded via AJAX</p></div>",
        "timestamp": 1234567890
    },
    "/api/user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    },
    "/api/search": {
        "results": [
            {"id": 1, "title": "Result 1", "url": "https://example.com/1"},
            {"id": 2, "title": "Result 2", "url": "https://example.com/2"}
        ],
        "total": 2
    }
}

COOKIE_TEST_PAGE = """
<html>
<head>
    <script>
        function setCookie(name, value, days) {
            const expires = new Date(Date.now() + days * 864e5).toUTCString();
            document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=/';
        }
        
        function getCookie(name) {
            return document.cookie.split('; ').reduce((r, v) => {
                const parts = v.split('=');
                return parts[0] === name ? decodeURIComponent(parts[1]) : r;
            }, '');
        }
        
        window.onload = function() {
            setCookie('test_cookie', 'test_value', 7);
            document.getElementById('cookie-value').textContent = getCookie('test_cookie');
        };
    </script>
</head>
<body>
    <h1>Cookie Test Page</h1>
    <p>Cookie value: <span id="cookie-value"></span></p>
</body>
</html>
"""

LOCAL_STORAGE_TEST_PAGE = """
<html>
<head>
    <script>
        window.onload = function() {
            // Test localStorage
            localStorage.setItem('test_key', 'test_value');
            document.getElementById('storage-value').textContent = localStorage.getItem('test_key');
            
            // Test sessionStorage
            sessionStorage.setItem('session_key', 'session_value');
            document.getElementById('session-value').textContent = sessionStorage.getItem('session_key');
        };
    </script>
</head>
<body>
    <h1>Storage Test Page</h1>
    <p>LocalStorage value: <span id="storage-value"></span></p>
    <p>SessionStorage value: <span id="session-value"></span></p>
</body>
</html>
"""