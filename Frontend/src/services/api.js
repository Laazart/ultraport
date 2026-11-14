const RAW_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
export const API_BASE = `${RAW_URL.replace(/\/+$/, '')}/`;