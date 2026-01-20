import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './auth.css';

function Profile() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchProfile = async () => {
            const token = localStorage.getItem('token');
            if (!token) {
                navigate('/login');
                return;
            }

            try {
                const response = await fetch('/users/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch profile');
                }

                const data = await response.json();
                setUser(data);
            } catch (err) {
                console.error(err);
                localStorage.removeItem('token');
                navigate('/login');
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, [navigate]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const handleAvatarClick = () => {
        fileInputRef.current.click();
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/users/me/avatar', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const data = await response.json();
            // Update user state with new picture URL
            setUser(prev => ({ ...prev, picture: data.picture }));

        } catch (error) {
            console.error("Error uploading avatar:", error);
            alert("Failed to upload profile picture");
        } finally {
            setUploading(false);
        }
    };

    if (loading) return <div className="auth-container" style={{ color: 'white' }}>Loading...</div>;

    return (
        <div className="auth-container">
            <div className="auth-card" style={{ textAlign: 'center', maxWidth: '500px' }}>
                <h2 className="auth-title">My Profile 👤</h2>

                <div className="profile-info" style={{ marginBottom: '2rem' }}>

                    {/* Avatar Upload Section */}
                    <div style={{ position: 'relative', width: '120px', margin: '0 auto 1rem' }}>
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            accept="image/*"
                        />

                        <div
                            onClick={handleAvatarClick}
                            style={{ cursor: 'pointer', position: 'relative' }}
                            title="Click to change picture"
                        >
                            {user?.picture ? (
                                <img
                                    src={user.picture}
                                    alt="Profile"
                                    style={{
                                        width: '120px',
                                        height: '120px',
                                        borderRadius: '50%',
                                        border: '4px solid #00C851',
                                        objectFit: 'cover',
                                        boxShadow: '0 0 20px rgba(0, 200, 81, 0.3)',
                                        opacity: uploading ? 0.5 : 1
                                    }}
                                />
                            ) : (
                                <div style={{
                                    width: '120px',
                                    height: '120px',
                                    borderRadius: '50%',
                                    background: 'linear-gradient(45deg, #333, #555)',
                                    border: '4px solid #00C851',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '4rem',
                                    color: 'white',
                                    boxShadow: '0 0 20px rgba(0, 200, 81, 0.3)',
                                    opacity: uploading ? 0.5 : 1
                                }}>
                                    {user?.name ? user.name.charAt(0).toUpperCase() : user?.username?.charAt(0).toUpperCase()}
                                </div>
                            )}

                            {/* Edit Icon Overlay */}
                            <div style={{
                                position: 'absolute',
                                bottom: '5px',
                                right: '5px',
                                background: '#00C851',
                                borderRadius: '50%',
                                width: '30px',
                                height: '30px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                border: '2px solid #1e1e1e'
                            }}>
                                ✏️
                            </div>
                        </div>
                        {uploading && <p style={{ color: '#00C851', fontSize: '0.8rem', marginTop: '5px' }}>Uploading...</p>}
                    </div>

                    {/* Name & Email */}
                    <h3 style={{ color: 'white', fontSize: '1.8rem', margin: '10px 0' }}>
                        {user?.name || "EcoEye User"}
                    </h3>
                    <p style={{ color: '#aaa', fontSize: '1.1rem', margin: '5px 0' }}>
                        {user?.username}
                    </p>

                    {/* Additional Details */}
                    <div style={{
                        marginTop: '20px',
                        padding: '15px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '10px',
                        textAlign: 'left'
                    }}>
                        <p style={{ margin: '8px 0', color: '#ccc' }}>
                            <strong>🆔 User ID:</strong> <span style={{ fontFamily: 'monospace', color: '#888' }}>{user?._id}</span>
                        </p>
                        <p style={{ margin: '8px 0', color: '#ccc' }}>
                            <strong>📅 Member Since:</strong> {user?.created_at || "N/A"}
                        </p>
                        <p style={{ margin: '8px 0', color: '#ccc' }}>
                            <strong>🛡️ Role:</strong> Ranger / Admin
                        </p>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '1rem', flexDirection: 'column' }}>
                    <button
                        onClick={() => navigate('/')}
                        className="auth-btn"
                        style={{ background: '#00C851', color: 'black', fontWeight: 'bold' }}
                    >
                        Go to Dashboard 📊
                    </button>

                    <button
                        onClick={handleLogout}
                        className="auth-btn"
                        style={{ background: 'transparent', border: '1px solid #ff4444', color: '#ff4444' }}
                    >
                        Logout 🚪
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Profile;
