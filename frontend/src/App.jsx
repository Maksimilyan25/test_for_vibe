import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import PublicRequestForm from './components/PublicRequestForm';
import './App.css';

function App() {
    return (
        <BrowserRouter>
            <div className="App">
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/create-request" element={<PublicRequestForm />} />
                </Routes>
            </div>
        </BrowserRouter>
    );
}

export default App;
