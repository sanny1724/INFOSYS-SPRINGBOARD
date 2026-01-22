
import { useState } from 'react';
import { Link } from 'react-router-dom';
import './auth.css';

function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');
        setIsLoading(true);

        try {
            const response = await fetch('/auth/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
            });

            const data = await response.json();

            if (response.ok) {
                setMessage(data.message);
            } else {
                setError(data.detail || 'Something went wrong');
            }
        } catch (err) {
            setError('Failed to connect to the server');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2 className="auth-title">Reset Password</h2>
                <p style={{ textAlign: 'center', marginBottom: '20px', color: '#666' }}>
                    Enter your email to receive a password reset link.
                </p>

                {message && <div className="success-msg" style={{ background: '#dff0d8', color: '#3c763d', padding: '10px', borderRadius: '5px', marginBottom: '10px' }}>{message}</div>}
                {error && <div className="error-msg">{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label>Email Address</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            placeholder="Enter your registered email"
                        />
                    </div>
                    <button type="submit" className="auth-btn" disabled={isLoading}>
                        {isLoading ? 'Sending...' : 'Send Reset Link'}
                    </button>
                    <div className="auth-link">
                        <Link to="/login">Back to Login</Link>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ForgotPassword;
