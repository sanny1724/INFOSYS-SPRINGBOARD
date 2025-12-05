import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './auth.css';

function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSocialLogin = async (provider) => {
        try {
            const response = await fetch(`/login/${provider}`);
            const data = await response.json();
            window.location.href = data.url;
        } catch (err) {
            setError(`Failed to connect to ${provider}`);
        }
    };

    // Check for token in URL (from OAuth redirect)
    if (window.location.search.includes('token=')) {
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            localStorage.setItem('token', token);
            window.location.href = '/'; // Force reload to clear URL
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Invalid credentials');
            }

            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            navigate('/');
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2 className="auth-title">Welcome Back</h2>
                {error && <div className="error-msg">{error}</div>}
                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label>Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            placeholder="Enter your username"
                        />
                    </div>
                    <div className="form-group">
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            placeholder="Enter your password"
                        />
                    </div>
                    <button type="submit" className="auth-btn">Sign In</button>
                </form>

                <div className="divider">OR</div>

                <div className="social-login">
                    <button onClick={() => handleSocialLogin('google')} className="social-btn">
                        <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="24" alt="Google" />
                        Google
                    </button>
                    <button onClick={() => handleSocialLogin('github')} className="social-btn">
                        <img src="https://www.svgrepo.com/show/512317/github-142.svg" width="24" alt="GitHub" />
                        GitHub
                    </button>
                </div>

                <div className="auth-link">
                    Don't have an account? <Link to="/signup">Sign Up</Link>
                </div>
            </div>
        </div>
    );
}

export default Login;
