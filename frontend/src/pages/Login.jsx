import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Login = () => {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        if (!password) {
            setError('Please enter the Access Code');
            return;
        }

        // Save to localStorage
        localStorage.setItem('admin_password', password);

        // Redirect to Dashboard
        navigate('/');
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            backgroundColor: '#f3f4f6'
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '2rem',
                borderRadius: '8px',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                width: '100%',
                maxWidth: '400px'
            }}>
                <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: '#111827' }}>HR Access</h2>
                <form onSubmit={handleLogin}>
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#374151' }}>Access Code</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                borderRadius: '4px',
                                border: '1px solid #d1d5db',
                                fontSize: '1rem'
                            }}
                            placeholder="Enter Admin Password"
                        />
                    </div>
                    {error && <p style={{ color: 'red', marginBottom: '1rem' }}>{error}</p>}
                    <button
                        type="submit"
                        style={{
                            width: '100%',
                            backgroundColor: '#2563eb',
                            color: 'white',
                            padding: '0.75rem',
                            borderRadius: '4px',
                            border: 'none',
                            fontSize: '1rem',
                            cursor: 'pointer'
                        }}
                    >
                        Enter Dashboard
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
