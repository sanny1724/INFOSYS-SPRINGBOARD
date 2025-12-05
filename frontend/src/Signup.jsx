import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './auth.css';

function Signup() {
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                let errorMessage = 'Registration failed';
                try {
                    const data = await response.json();
                    errorMessage = data.detail || errorMessage;
                } catch (e) {
                    console.error("Failed to parse error response", e);
                }
                throw new Error(errorMessage);
            }

            navigate('/login');
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                    <h1 style={{
                        fontSize: '2.5rem',
                        fontWeight: '800',
                        background: 'linear-gradient(45deg, #00ff87, #60efff)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        margin: 0
                    }}>
                        ECOEYE AI 🌿
                    </h1>
                    <p style={{ color: '#ccc', fontSize: '0.9rem' }}>Protecting Wildlife with Intelligence</p>
                </div>
                <h2 className="auth-title">Create Account</h2>
                {error && <div className="error-msg">{error}</div>}
                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label>Email Address 📧</label>
                        <input
                            type="email"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            placeholder="Enter your email"
                        />
                    </div>
                    <div className="form-group">
                        <label>Password 🔒</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            placeholder="Choose a password"
                        />
                    </div>
                    <button type="submit" className="auth-btn">Sign Up 🚀</button>
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
                    Already have an account? <Link to="/login">Sign In</Link>
                </div>
            </div>
        </div>
    );
}

export default Signup;
