// Динамический URL бэка (берет хост и порт из текущего окна)
const API_PORT = process.env.REACT_APP_API_PORT || window.location.port || 8000;
const API_URL = `http://${window.location.hostname}:${API_PORT}/api/v1`;

// Сохраняем токен
const setToken = (token) => localStorage.setItem('token', token);
const getToken = () => localStorage.getItem('token');
const removeToken = () => localStorage.removeItem('token');

// Базовые заголовки
const getHeaders = (isFormData = false) => {
    const headers = {};
    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }
    if (getToken()) {
        headers['Authorization'] = `Bearer ${getToken()}`;
    }
    return headers;
};

// Утилита для запросов
async function request(url, options = {}) {
    const response = await fetch(`${API_URL}${url}`, {
        ...options,
        headers: { ...getHeaders(), ...options.headers }
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || 'Ошибка запроса');
    }

    return data;
}

// API функции
export const api = {
    // Регистрация
    async register(userData) {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(userData)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Ошибка регистрации');
        }

        return data;
    },

    // Вход
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Ошибка входа');
        }

        setToken(data.access_token);
        return data;
    },

    // Получить текущего пользователя
    async getMe() {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: getHeaders()
        });

        const data = await response.json();

        if (!response.ok) {
            removeToken();
            throw new Error(data.detail || 'Ошибка получения пользователя');
        }

        return data;
    },

    // Выход
    logout() {
        removeToken();
    },

    // Проверка авторизации
    isAuthenticated() {
        return !!getToken();
    },

    // Получить токен
    getToken
};

// API для заявок (диспетчер)
export const requestsApi = {
    // Создать заявку
    async create(data) {
        return request('/requests', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // Получить список заявок
    async getList(params = {}) {
        const query = new URLSearchParams(params).toString();
        return request(`/requests?${query}`);
    },

    // Получить заявку по ID
    async getById(id) {
        return request(`/requests/${id}`);
    },

    // Назначить мастера
    async assignMaster(requestId, masterId) {
        return request(`/requests/${requestId}/assign`, {
            method: 'POST',
            body: JSON.stringify({ master_id: masterId })
        });
    },

    // Отменить заявку
    async cancel(requestId) {
        return request(`/requests/${requestId}/cancel`, {
            method: 'POST'
        });
    },

    // Получить список мастеров
    async getMasters() {
        return request('/requests/masters/available');
    }
};

// API для мастера
export const masterApi = {
    // Получить мои заявки
    async getMyRequests(params = {}) {
        const query = new URLSearchParams(params).toString();
        return request(`/master/requests?${query}`);
    },

    // Взять в работу
    async takeToWork(requestId) {
        return request(`/master/requests/${requestId}/take`, {
            method: 'POST'
        });
    },

    // Завершить
    async complete(requestId) {
        return request(`/master/requests/${requestId}/complete`, {
            method: 'POST'
        });
    },

    // Получить детали заявки
    async getById(requestId) {
        return request(`/master/requests/${requestId}`);
    },

    // Получить статистику
    async getStats() {
        return request('/master/stats');
    }
};