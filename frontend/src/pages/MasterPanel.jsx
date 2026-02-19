import React, { useState, useEffect } from 'react';
import { masterApi } from '../services/api';
import './MasterPanel.css';

const MasterPanel = () => {
    const [requests, setRequests] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedRequest, setSelectedRequest] = useState(null);
    const [filters, setFilters] = useState({
        status: ''
    });

    // Загрузка данных
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [requestsData, statsData] = await Promise.all([
                masterApi.getMyRequests(),
                masterApi.getStats()
            ]);
            setRequests(requestsData);
            setStats(statsData);
        } catch (error) {
            console.error('Ошибка загрузки:', error);
        } finally {
            setLoading(false);
        }
    };

    // Применить фильтры
    const applyFilters = async () => {
        setLoading(true);
        try {
            const params = {};
            if (filters.status) params.status = filters.status;

            const data = await masterApi.getMyRequests(params);
            setRequests(data);
        } catch (error) {
            console.error('Ошибка фильтрации:', error);
        } finally {
            setLoading(false);
        }
    };

    // Взять в работу
    const handleTakeToWork = async (requestId) => {
        try {
            await masterApi.takeToWork(requestId);
            loadData(); // перезагрузить список
        } catch (error) {
            alert('Ошибка: ' + error.message);
        }
    };

    // Завершить
    const handleComplete = async (requestId) => {
        if (!window.confirm('Завершить заявку?')) return;
        try {
            await masterApi.complete(requestId);
            loadData(); // перезагрузить список
        } catch (error) {
            alert('Ошибка: ' + error.message);
        }
    };

    // Показать детали
    const handleViewDetails = async (requestId) => {
        try {
            const data = await masterApi.getById(requestId);
            setSelectedRequest(data);
        } catch (error) {
            alert('Ошибка: ' + error.message);
        }
    };

    // Статус на русском
    const getStatusText = (status) => {
        const statusMap = {
            'new': 'Новая',
            'assigned': 'Назначена',
            'in_progress': 'В работе',
            'done': 'Выполнена',
            'canceled': 'Отменена'
        };
        return statusMap[status] || status;
    };

    // Цвет статуса
    const getStatusColor = (status) => {
        const colorMap = {
            'new': '#007bff',
            'assigned': '#ffc107',
            'in_progress': '#17a2b8',
            'done': '#28a745',
            'canceled': '#dc3545'
        };
        return colorMap[status] || '#6c757d';
    };

    if (loading) return <div className="loading">Загрузка...</div>;

    return (
        <div className="master-panel">
            <header className="panel-header">
                <h2>Панель мастера</h2>
            </header>

            {/* Статистика */}
            {stats && (
                <div className="stats-cards">
                    <div className="stat-card">
                        <span className="stat-label">Всего</span>
                        <span className="stat-value">{stats.total}</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Назначено</span>
                        <span className="stat-value">{stats.assigned}</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">В работе</span>
                        <span className="stat-value">{stats.in_progress}</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Выполнено</span>
                        <span className="stat-value">{stats.done}</span>
                    </div>
                </div>
            )}

            {/* Фильтры */}
            <div className="filters">
                <select
                    value={filters.status}
                    onChange={(e) => setFilters({...filters, status: e.target.value})}
                >
                    <option value="">Все статусы</option>
                    <option value="assigned">Назначенные</option>
                    <option value="in_progress">В работе</option>
                    <option value="done">Выполненные</option>
                    <option value="canceled">Отмененные</option>
                </select>

                <button onClick={applyFilters}>Применить</button>
                <button onClick={loadData}>Сбросить</button>
            </div>

            {/* Список заявок */}
            <div className="requests-list">
                {requests.length === 0 ? (
                    <p className="empty">Нет заявок</p>
                ) : (
                    requests.map(request => (
                        <div key={request.id} className="request-card">
                            <div className="request-header">
                                <span className="request-id">#{request.id}</span>
                                <span
                                    className="request-status"
                                    style={{ backgroundColor: getStatusColor(request.status) }}
                                >
                                    {getStatusText(request.status)}
                                </span>
                            </div>

                            <div className="request-body">
                                <p><strong>Клиент:</strong> {request.client_name}</p>
                                <p><strong>Телефон:</strong> {request.phone}</p>
                                <p><strong>Адрес:</strong> {request.address}</p>
                                <p><strong>Проблема:</strong> {request.problem_text.substring(0, 100)}...</p>
                            </div>

                            <div className="request-actions">
                                <button
                                    className="details-btn"
                                    onClick={() => handleViewDetails(request.id)}
                                >
                                    Детали
                                </button>

                                {request.status === 'assigned' && (
                                    <button
                                        className="take-btn"
                                        onClick={() => handleTakeToWork(request.id)}
                                    >
                                        Взять в работу
                                    </button>
                                )}

                                {request.status === 'in_progress' && (
                                    <button
                                        className="complete-btn"
                                        onClick={() => handleComplete(request.id)}
                                    >
                                        Завершить
                                    </button>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Модалка деталей */}
            {selectedRequest && (
                <div className="modal-overlay" onClick={() => setSelectedRequest(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>Заявка #{selectedRequest.id}</h3>

                        <div className="details-body">
                            <p><strong>Статус:</strong> {getStatusText(selectedRequest.status)}</p>
                            <p><strong>Клиент:</strong> {selectedRequest.client_name}</p>
                            <p><strong>Телефон:</strong> {selectedRequest.phone}</p>
                            <p><strong>Адрес:</strong> {selectedRequest.address}</p>
                            <p><strong>Проблема:</strong> {selectedRequest.problem_text}</p>
                            <p><strong>Создана:</strong> {new Date(selectedRequest.created_at).toLocaleString()}</p>
                            {selectedRequest.updated_at && (
                                <p><strong>Обновлена:</strong> {new Date(selectedRequest.updated_at).toLocaleString()}</p>
                            )}
                        </div>

                        <div className="modal-actions">
                            <button onClick={() => setSelectedRequest(null)}>Закрыть</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MasterPanel;
