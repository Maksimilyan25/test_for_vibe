// Динамический URL бэка
const API_PORT = process.env.REACT_APP_API_PORT || window.location.port || 8000;
const API_URL = `http://${window.location.hostname}:${API_PORT}/api/v1`;

const setToken = (token) => localStorage.setItem('token', token);
const getToken = () => localStorage.getItem('token');
const removeToken = () => localStorage.removeItem('token');

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

export const api = {
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

    logout() {
        removeToken();
    },

    isAuthenticated() {
        return !!getToken();
    },

    getToken
};

// Публичное API (без авторизации)
export const publicApi = {
    async createRequest(data) {
        const response = await fetch(`${API_URL}/requests`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Ошибка создания заявки');
        }

        return result;
    }
};

export const requestsApi = {
    async create(data) {
        return request('/requests', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async getList(params = {}) {
        const query = new URLSearchParams(params).toString();
        return request(`/requests?${query}`);
    },

    async getById(id) {
        return request(`/requests/${id}`);
    },

    async assignMaster(requestId, masterId) {
        return request(`/requests/${requestId}/assign`, {
            method: 'POST',
            body: JSON.stringify({ master_id: masterId })
        });
    },

    async cancel(requestId) {
        return request(`/requests/${requestId}/cancel`, {
            method: 'POST'
        });
    },

    async getMasters() {
        return request('/requests/masters/available');
    }
};

export const masterApi = {
    async getMyRequests(params = {}) {
        const query = new URLSearchParams(params).toString();
        return request(`/master/requests?${query}`);
    },

    async takeToWork(requestId) {
        return request(`/master/requests/${requestId}/take`, {
            method: 'POST'
        });
    },

    async complete(requestId) {
        return request(`/master/requests/${requestId}/complete`, {
            method: 'POST'
        });
    },

    async getById(requestId) {
        return request(`/master/requests/${requestId}`);
    },

    async getStats() {
        return request('/master/stats');
    }
};
