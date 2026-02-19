import React, { useState, useEffect } from 'react';
import AuthModal from '../components/AuthModal';
import { api } from '../services/api';
import DispatcherPanel from './DispatcherPanel';
import MasterPanel from './MasterPanel';
import './Home.css';

const Home = () => {
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Проверяем авторизацию при загрузке
    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        if (api.isAuthenticated()) {
            try {
                const userData = await api.getMe();
                setUser(userData);
            } catch {
                api.logout();
            }
        }
        setLoading(false);
    };

    const handleAuthSuccess = (userData) => {
        setUser(userData);
    };

    const handleLogout = () => {
        api.logout();
        setUser(null);
    };

    if (loading) {
        return <div className="loading">Загрузка...</div>;
    }

    return (
        <div className="home">
            <header className="header">
                <h1>Ремонтная служба</h1>

                {user ? (
                    <div className="user-info">
                        <span>Привет, {user.full_name} ({user.role === 'master' ? 'Мастер' : 'Диспетчер'})</span>
                        <button onClick={handleLogout}>Выйти</button>
                    </div>
                ) : (
                    <button onClick={() => setShowAuthModal(true)}>Вход</button>
                )}
            </header>

            <main>
                {user ? (
                    <div className="content">
                        {user.role === 'dispatcher' && <DispatcherPanel />}
                        {user.role === 'master' && <MasterPanel />}
                    </div>
                ) : (
                    <div className="welcome">
                        <h2>Добро пожаловать в систему заявок ремонтной службы</h2>
                        <p>Пожалуйста, войдите для продолжения работы</p>
                    </div>
                )}
            </main>

            {showAuthModal && (
                <AuthModal
                    onClose={() => setShowAuthModal(false)}
                    onAuthSuccess={handleAuthSuccess}
                />
            )}
        </div>
    );
};

export default Home;