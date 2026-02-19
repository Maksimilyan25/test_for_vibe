import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { publicApi } from '../services/api';
import './PublicRequestForm.css';

const PublicRequestForm = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        client_name: '',
        phone: '',
        address: '',
        problem_text: ''
    });
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});

    const handleChange = (e) => {
        const { name, value } = e.target;

        // Для телефона разрешаем только цифры
        if (name === 'phone') {
            const numbersOnly = value.replace(/\D/g, '');
            setFormData({
                ...formData,
                [name]: numbersOnly
            });
        } else {
            setFormData({
                ...formData,
                [name]: value
            });
        }

        // Очищаем ошибку поля при изменении
        if (fieldErrors[name]) {
            setFieldErrors({
                ...fieldErrors,
                [name]: ''
            });
        }

        // Очищаем общую ошибку
        if (error) {
            setError('');
        }
    };

    const validateForm = () => {
        const errors = {};

        if (!formData.client_name.trim()) {
            errors.client_name = 'Имя обязательно';
        }

        if (!formData.phone) {
            errors.phone = 'Телефон обязателен';
        } else if (!/^\d{10,15}$/.test(formData.phone)) {
            errors.phone = 'Телефон должен содержать от 10 до 15 цифр';
        }

        if (!formData.address.trim()) {
            errors.address = 'Адрес обязателен';
        }

        if (!formData.problem_text.trim()) {
            errors.problem_text = 'Описание проблемы обязательно';
        }

        return errors;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Валидация перед отправкой
        const errors = validateForm();
        if (Object.keys(errors).length > 0) {
            setFieldErrors(errors);
            return;
        }

        setLoading(true);
        setError('');
        setFieldErrors({});

        try {
            // Отправляем телефон как число (уже без преобразования, так как это строка цифр)
            await publicApi.createRequest(formData);
            setSubmitted(true);
            setTimeout(() => {
                navigate('/');
            }, 7000);
        } catch (err) {
            console.error('Error details:', err.response?.data);

            // Обработка ошибок от сервера
            if (err.response?.data?.detail) {
                // Если это ошибка валидации Pydantic
                if (Array.isArray(err.response.data.detail)) {
                    const serverErrors = {};
                    err.response.data.detail.forEach(error => {
                        if (error.loc && error.loc[1]) {
                            serverErrors[error.loc[1]] = error.msg;
                        }
                    });
                    setFieldErrors(serverErrors);
                } else {
                    // Общая ошибка
                    setError(err.response.data.detail || 'Произошла ошибка при создании заявки');
                }
            } else {
                setError(err.message || 'Произошла ошибка при создании заявки');
            }
            setLoading(false);
        }
    };

    const handleBackToHome = () => {
        navigate('/');
    };

    const formatPhone = (value) => {
        // Форматирование для отображения (опционально)
        const numbers = value.replace(/\D/g, '');
        if (numbers.length <= 11) {
            // Российский формат: +7 (999) 123-45-67
            if (numbers.length > 0) {
                let formatted = numbers;
                if (numbers.length > 1) {
                    formatted = numbers.substring(0, 1) + ' (' + numbers.substring(1, 4);
                }
                if (numbers.length > 4) {
                    formatted = formatted + ') ' + numbers.substring(4, 7);
                }
                if (numbers.length > 7) {
                    formatted = formatted + '-' + numbers.substring(7, 9);
                }
                if (numbers.length > 9) {
                    formatted = formatted + '-' + numbers.substring(9, 11);
                }
                return formatted;
            }
        }
        return numbers;
    };

    if (submitted) {
        return (
            <div className="success-screen">
                <div className="success-card">
                    <div className="success-icon">✓</div>
                    <h2>Заявка создана!</h2>
                    <p>После обработки заявки диспетчером с вами свяжется мастер</p>
                    <p className="redirect-info">Через 7 секунд вы будете перенаправлены на главную</p>
                    <button onClick={handleBackToHome} className="home-button">
                        На главную сейчас
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="public-form">
            <h2>Оставить заявку на ремонт</h2>

            {error && (
                <div className="error-message">
                    <strong>Ошибка!</strong> {error}
                </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
                <div className={`form-group ${fieldErrors.client_name ? 'has-error' : ''}`}>
                    <label>Ваше имя</label>
                    <input
                        type="text"
                        name="client_name"
                        value={formData.client_name}
                        onChange={handleChange}
                        required
                        placeholder="Иван Петров"
                        className={fieldErrors.client_name ? 'error' : ''}
                    />
                    {fieldErrors.client_name && (
                        <div className="field-error">{fieldErrors.client_name}</div>
                    )}
                </div>

                <div className={`form-group ${fieldErrors.phone ? 'has-error' : ''}`}>
                    <label>Телефон</label>
                    <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        required
                        placeholder="+7 (999) 123-45-67"
                        className={fieldErrors.phone ? 'error' : ''}
                        maxLength="15"
                    />
                    {fieldErrors.phone && (
                        <div className="field-error">{fieldErrors.phone}</div>
                    )}
                    <small className="hint">Только цифры, от 10 до 15 символов</small>
                </div>

                <div className={`form-group ${fieldErrors.address ? 'has-error' : ''}`}>
                    <label>Адрес</label>
                    <input
                        type="text"
                        name="address"
                        value={formData.address}
                        onChange={handleChange}
                        required
                        placeholder="ул. Ленина, д. 10, кв. 5"
                        className={fieldErrors.address ? 'error' : ''}
                    />
                    {fieldErrors.address && (
                        <div className="field-error">{fieldErrors.address}</div>
                    )}
                </div>

                <div className={`form-group ${fieldErrors.problem_text ? 'has-error' : ''}`}>
                    <label>Описание проблемы</label>
                    <textarea
                        name="problem_text"
                        value={formData.problem_text}
                        onChange={handleChange}
                        required
                        rows="4"
                        placeholder="Опишите проблему..."
                        className={fieldErrors.problem_text ? 'error' : ''}
                    />
                    {fieldErrors.problem_text && (
                        <div className="field-error">{fieldErrors.problem_text}</div>
                    )}
                </div>

                <button type="submit" disabled={loading}>
                    {loading ? 'Отправка...' : 'Оставить заявку'}
                </button>
            </form>
        </div>
    );
};

export default PublicRequestForm;