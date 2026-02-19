import React, { useState } from 'react';
import { api } from '../services/api';
import './AuthModal.css';

const AuthModal = ({ onClose, onAuthSuccess }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        full_name: '',
        role: 'master'
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isLogin) {
                // Вход
                await api.login(formData.username, formData.password);
                const user = await api.getMe();
                onAuthSuccess(user);
            } else {
                // Регистрация
                await api.register({
                    username: formData.username,
                    password: formData.password,
                    full_name: formData.full_name,
                    role: formData.role
                });
                // После регистрации сразу логинимся
                await api.login(formData.username, formData.password);
                const user = await api.getMe();
                onAuthSuccess(user);
            }
            onClose();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <h2>{isLogin ? 'Вход' : 'Регистрация'}</h2>

                {error && <div className="error">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <input
                        type="text"
                        name="username"
                        placeholder="Имя пользователя"
                        value={formData.username}
                        onChange={handleChange}
                        required
                        minLength={3}
                    />

                    <input
                        type="password"
                        name="password"
                        placeholder="Пароль"
                        value={formData.password}
                        onChange={handleChange}
                        required
                        minLength={6}
                    />

                    {!isLogin && (
                        <>
                            <input
                                type="text"
                                name="full_name"
                                placeholder="Полное имя"
                                value={formData.full_name}
                                onChange={handleChange}
                                required
                            />

                            <select name="role" value={formData.role} onChange={handleChange}>
                                <option value="master">Мастер</option>
                                <option value="dispatcher">Диспетчер</option>
                            </select>
                        </>
                    )}

                    <button type="submit" disabled={loading}>
                        {loading ? 'Загрузка...' : isLogin ? 'Войти' : 'Зарегистрироваться'}
                    </button>
                </form>

                <p>
                    {isLogin ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}
                    <button className="link" onClick={() => setIsLogin(!isLogin)}>
                        {isLogin ? 'Зарегистрироваться' : 'Войти'}
                    </button>
                </p>

                <button className="close" onClick={onClose}>×</button>
            </div>
        </div>
    );
};

export default AuthModal;
