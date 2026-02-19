import React, { useState, useEffect } from 'react';
import { requestsApi } from '../services/api';
import './DispatcherPanel.css';

const DispatcherPanel = () => {
    const [requests, setRequests] = useState([]);
    const [masters, setMasters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        status: '',
        master_id: ''
    });
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newRequest, setNewRequest] = useState({
        client_name: '',
        phone: '',
        address: '',
        problem_text: ''
    });

    // Загрузка данных
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [requestsData, mastersData] = await Promise.all([
                requestsApi.getList(),
                requestsApi.getMasters()
            ]);
            setRequests(requestsData);
            setMasters(mastersData);
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
            if (filters.master_id) params.master_id = filters.master_id;

            const data = await requestsApi.getList(params);
            setRequests(data);
        } catch (error) {
            console.error('Ошибка фильтрации:', error);
        } finally {
            setLoading(false);
        }
    };

    // Создать заявку
    const handleCreateRequest = async (e) => {
        e.preventDefault();
        try {
            await requestsApi.create(newRequest);
            setShowCreateModal(false);
            setNewRequest({ client_name: '', phone: '', address: '', problem_text: '' });
            loadData(); // перезагрузить список
        } catch (error) {
            alert('Ошибка создания: ' + error.message);
        }
    };

    // Назначить мастера
    const handleAssignMaster = async (requestId, masterId) => {
        try {
            await requestsApi.assignMaster(requestId, masterId);
            loadData(); // перезагрузить список
        } catch (error) {
            alert('Ошибка назначения: ' + error.message);
        }
    };

    // Отменить заявку
    const handleCancelRequest = async (requestId) => {
        if (!window.confirm('Отменить заявку?')) return;
        try {
            await requestsApi.cancel(requestId);
            loadData(); // перезагрузить список
        } catch (error) {
            alert('Ошибка отмены: ' + error.message);
        }
    };

    // Получить имя мастера по ID
    const getMasterName = (masterId) => {
        if (!masterId) return 'Не назначен';
        const master = masters.find(m => m.id === masterId);
        return master ? master.full_name : 'Неизвестно';
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

    if (loading) return <div className="loading">Загрузка...</div>;

    return (
        <div className="dispatcher-panel">
            <header className="panel-header">
                <h2>Панель диспетчера</h2>
                <button onClick={() => setShowCreateModal(true)}>+ Новая заявка</button>
            </header>

            {/* Фильтры */}
            <div className="filters">
                <select
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                >
                    <option value="">Все статусы</option>
                    <option value="new">Новые</option>
                    <option value="assigned">Назначенные</option>
                    <option value="in_progress">В работе</option>
                    <option value="done">Выполненные</option>
                    <option value="canceled">Отмененные</option>
                </select>

                <select
                    value={filters.master_id}
                    onChange={(e) => setFilters({ ...filters, master_id: e.target.value })}
                >
                    <option value="">Все мастера</option>
                    {masters.map(master => (
                        <option key={master.id} value={master.id}>{master.full_name}</option>
                    ))}
                </select>

                <button onClick={applyFilters}>Применить</button>
            </div>

            {/* Список заявок */}
            <div className="requests-list">
                {requests.length === 0 ? (
                    <p className="empty">Нет заявок</p>
                ) : (
                    requests.map(request => (
                        <div key={request.id} className={`request-card status-${request.status}`}>
                            <div className="request-header">
                                <span className="request-id">#{request.id}</span>
                                <span className="request-status">{getStatusText(request.status)}</span>
                            </div>

                            <div className="request-body">
                                <p><strong>Клиент:</strong> {request.client_name}</p>
                                <p><strong>Телефон:</strong> {request.phone}</p>
                                <p><strong>Адрес:</strong> {request.address}</p>
                                <p><strong>Проблема:</strong> {request.problem_text}</p>
                                <p><strong>Мастер:</strong> {getMasterName(request.assigned_to)}</p>
                            </div>

                            <div className="request-actions">
                                {request.status === 'new' && (
                                    <select
                                        onChange={(e) => handleAssignMaster(request.id, Number(e.target.value))}
                                        defaultValue=""
                                    >
                                        <option value="" disabled>Назначить мастера</option>
                                        {masters.map(master => (
                                            <option key={master.id} value={master.id}>{master.full_name}</option>
                                        ))}
                                    </select>
                                )}

                                {request.status !== 'canceled' && request.status !== 'done' && (
                                    <button
                                        className="cancel-btn"
                                        onClick={() => handleCancelRequest(request.id)}
                                    >
                                        Отменить
                                    </button>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Модалка создания заявки */}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>Новая заявка</h3>
                        <form onSubmit={handleCreateRequest}>
                            <input
                                type="text"
                                placeholder="Имя клиента"
                                value={newRequest.client_name}
                                onChange={(e) => setNewRequest({ ...newRequest, client_name: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="Телефон"
                                value={newRequest.phone}
                                onChange={(e) => setNewRequest({ ...newRequest, phone: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="Адрес"
                                value={newRequest.address}
                                onChange={(e) => setNewRequest({ ...newRequest, address: e.target.value })}
                                required
                            />
                            <textarea
                                placeholder="Описание проблемы"
                                value={newRequest.problem_text}
                                onChange={(e) => setNewRequest({ ...newRequest, problem_text: e.target.value })}
                                required
                                rows="3"
                            />
                            <div className="modal-actions">
                                <button type="submit">Создать</button>
                                <button type="button" onClick={() => setShowCreateModal(false)}>Отмена</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DispatcherPanel;
