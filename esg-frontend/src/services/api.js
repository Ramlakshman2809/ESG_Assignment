import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'https://esg-assignment.onrender.com/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (username, password) =>
  api.post('/auth/login/', { username, password });

export const register = (username, email, password) =>
  api.post('/auth/register/', { username, email, password });

// Tenants
export const getTenants = () => api.get('/tenants/');

// Data Sources
export const getDataSources = (tenantId) =>
  api.get(`/data-sources/?tenant=${tenantId}`);

// Emission Records
export const getEmissionRecords = (params) => {
  const queryParams = new URLSearchParams(params).toString();
  return api.get(`/emission-records/?${queryParams}`);
};

export const getEmissionRecord = (id) =>
  api.get(`/emission-records/${id}/`);

export const updateRecordStatus = (id, status, notes) =>
  api.post(`/emission-records/${id}/update_status/`, { status, notes });

export const bulkApprove = (recordIds) =>
  api.post('/emission-records/bulk_approve/', { record_ids: recordIds });

export const bulkReject = (recordIds, notes) =>
  api.post('/emission-records/bulk_reject/', { record_ids: recordIds, notes });

// Dashboard
export const getDashboardStats = (tenantId) =>
  api.get(`/emission-records/dashboard_stats/?tenant=${tenantId}`);

// Import
export const ingestSAP = (tenantId, sourceId, data) =>
  api.post('/ingestion/ingest_sap/', { tenant_id: tenantId, source_id: sourceId, data });

export const ingestUtility = (tenantId, sourceId, data) =>
  api.post('/ingestion/ingest_utility/', { tenant_id: tenantId, source_id: sourceId, data });

export const ingestTravel = (tenantId, sourceId, data) =>
  api.post('/ingestion/ingest_travel/', { tenant_id: tenantId, source_id: sourceId, data });

// Import Batches
export const getImportBatches = (tenantId, sourceId) => {
  const params = new URLSearchParams();
  if (tenantId) params.append('tenant', tenantId);
  if (sourceId) params.append('source', sourceId);
  return api.get(`/import-batches/?${params}`);
};

// Categories
export const getCategories = () => api.get('/emission-categories/');

export default api;