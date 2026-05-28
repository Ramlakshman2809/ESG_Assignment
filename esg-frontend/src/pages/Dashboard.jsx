import { useState, useEffect } from 'react';
import { getDashboardStats, getEmissionRecords, bulkApprove, bulkReject, updateRecordStatus } from '../services/api';
import './Dashboard.css';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTenant, setSelectedTenant] = useState('1');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedRecords, setSelectedRecords] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, count: 0 });
  const [selectedRecord, setSelectedRecord] = useState(null);

  useEffect(() => {
    loadDashboard();
  }, [selectedTenant]);

  useEffect(() => {
    loadRecords();
  }, [selectedTenant, statusFilter, pagination.page]);

  const loadDashboard = async () => {
    try {
      const response = await getDashboardStats(selectedTenant);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    }
  };

  const loadRecords = async () => {
    setLoading(true);
    try {
      const params = {
        tenant: selectedTenant,
        page: pagination.page,
        page_size: 20,
      };
      if (statusFilter) params.status = statusFilter;

      const response = await getEmissionRecords(params);
      setRecords(response.data.results || []);
      setPagination(prev => ({ ...prev, count: response.data.count }));
    } catch (error) {
      console.error('Failed to load records:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedRecords(records.map(r => r.id));
    } else {
      setSelectedRecords([]);
    }
  };

  const handleSelectRecord = (id) => {
    setSelectedRecords(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    );
  };

  const handleBulkApprove = async () => {
    try {
      await bulkApprove(selectedRecords);
      setSelectedRecords([]);
      loadDashboard();
      loadRecords();
    } catch (error) {
      console.error('Failed to approve:', error);
    }
  };

  const handleBulkReject = async () => {
    const notes = prompt('Enter rejection reason (optional):');
    try {
      await bulkReject(selectedRecords, notes || '');
      setSelectedRecords([]);
      loadDashboard();
      loadRecords();
    } catch (error) {
      console.error('Failed to reject:', error);
    }
  };

  const getStatusClass = (status) => {
    const classes = {
      pending: 'status-pending',
      approved: 'status-approved',
      rejected: 'status-rejected',
      suspicious: 'status-suspicious',
    };
    return classes[status] || '';
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>ESG Data Review Dashboard</h1>
        <div className="header-actions">
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
          >
            <option value="1">Acme Corporation</option>
          </select>
          <button onClick={() => window.location.href = '/import'} className="btn-primary">
            Import Data
          </button>
        </div>
      </header>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <h3>Total Records</h3>
            <p className="stat-value">{stats.total_records}</p>
          </div>
          <div className="stat-card stat-pending">
            <h3>Pending Review</h3>
            <p className="stat-value">{stats.pending_review}</p>
          </div>
          <div className="stat-card stat-approved">
            <h3>Approved</h3>
            <p className="stat-value">{stats.approved}</p>
          </div>
          <div className="stat-card stat-rejected">
            <h3>Rejected</h3>
            <p className="stat-value">{stats.rejected}</p>
          </div>
          <div className="stat-card stat-suspicious">
            <h3>Suspicious</h3>
            <p className="stat-value">{stats.suspicious}</p>
          </div>
        </div>
      )}

      {stats?.by_source && Object.keys(stats.by_source).length > 0 && (
        <div className="breakdown-section">
          <h3>Records by Source</h3>
          <div className="breakdown-grid">
            {Object.entries(stats.by_source).map(([source, count]) => (
              <div key={source} className="breakdown-item">
                <span className="breakdown-label">{source}</span>
                <span className="breakdown-value">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="records-section">
        <div className="records-header">
          <h2>Emission Records</h2>
          <div className="records-filters">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="suspicious">Suspicious</option>
            </select>
          </div>
        </div>

        {selectedRecords.length > 0 && (
          <div className="bulk-actions">
            <span>{selectedRecords.length} selected</span>
            <button onClick={handleBulkApprove} className="btn-approve">
              Approve Selected
            </button>
            <button onClick={handleBulkReject} className="btn-reject">
              Reject Selected
            </button>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading records...</div>
        ) : (
          <table className="records-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    onChange={handleSelectAll}
                    checked={selectedRecords.length === records.length && records.length > 0}
                  />
                </th>
                <th>Source</th>
                <th>Category</th>
                <th>Activity</th>
                <th>Period</th>
                <th>Status</th>
                <th>Imported</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr
                  key={record.id}
                  onClick={() => setSelectedRecord(record)}
                  className={selectedRecords.includes(record.id) ? 'selected' : ''}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedRecords.includes(record.id)}
                      onChange={() => handleSelectRecord(record.id)}
                    />
                  </td>
                  <td>{record.source_name}</td>
                  <td>{record.category_details?.category_type_display}</td>
                  <td>
                    {record.activity_value} {record.activity_unit_details?.symbol}
                  </td>
                  <td>
                    {record.period_start} to {record.period_end}
                  </td>
                  <td>
                    <span className={`status-badge ${getStatusClass(record.status)}`}>
                      {record.status_display}
                    </span>
                  </td>
                  <td>{new Date(record.imported_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {records.length === 0 && !loading && (
          <div className="empty-state">No records found</div>
        )}
      </div>

      {selectedRecord && (
        <div className="record-modal" onClick={() => setSelectedRecord(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedRecord(null)}>
              &times;
            </button>
            <h2>Record Details</h2>
            <div className="modal-body">
              <div className="detail-row">
                <label>Source:</label>
                <span>{selectedRecord.source_name}</span>
              </div>
              <div className="detail-row">
                <label>Category:</label>
                <span>{selectedRecord.category_details?.category_type_display}</span>
              </div>
              <div className="detail-row">
                <label>Activity Value:</label>
                <span>
                  {selectedRecord.activity_value} {selectedRecord.activity_unit_details?.symbol}
                </span>
              </div>
              <div className="detail-row">
                <label>Period:</label>
                <span>{selectedRecord.period_start} to {selectedRecord.period_end}</span>
              </div>
              <div className="detail-row">
                <label>Status:</label>
                <span className={`status-badge ${getStatusClass(selectedRecord.status)}`}>
                  {selectedRecord.status_display}
                </span>
              </div>
              {selectedRecord.flagged_reason && (
                <div className="detail-row flag-reason">
                  <label>Flag Reason:</label>
                  <span>{selectedRecord.flagged_reason}</span>
                </div>
              )}
              {selectedRecord.analyst_notes && (
                <div className="detail-row">
                  <label>Notes:</label>
                  <span>{selectedRecord.analyst_notes}</span>
                </div>
              )}
              <div className="detail-row">
                <label>Raw Data:</label>
                <pre>{JSON.stringify(selectedRecord.raw_data, null, 2)}</pre>
              </div>
              {selectedRecord.audit_trail?.length > 0 && (
                <div className="audit-section">
                  <h3>Audit Trail</h3>
                  {selectedRecord.audit_trail.map((entry) => (
                    <div key={entry.id} className="audit-entry">
                      <span className="audit-action">{entry.action_display}</span>
                      <span className="audit-user">by {entry.changed_by_username}</span>
                      <span className="audit-date">
                        {new Date(entry.changed_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-actions">
              {selectedRecord.status !== 'approved' && (
                <button
                  className="btn-approve"
                  onClick={async () => {
                    await updateRecordStatus(selectedRecord.id, 'approved', '');
                    setSelectedRecord(null);
                    loadDashboard();
                    loadRecords();
                  }}
                >
                  Approve
                </button>
              )}
              {selectedRecord.status !== 'rejected' && (
                <button
                  className="btn-reject"
                  onClick={async () => {
                    const notes = prompt('Rejection reason:');
                    await updateRecordStatus(selectedRecord.id, 'rejected', notes || '');
                    setSelectedRecord(null);
                    loadDashboard();
                    loadRecords();
                  }}
                >
                  Reject
                </button>
              )}
              {selectedRecord.status !== 'suspicious' && (
                <button
                  className="btn-flag"
                  onClick={async () => {
                    const reason = prompt('Flag reason:');
                    if (reason) {
                      await updateRecordStatus(selectedRecord.id, 'suspicious', reason);
                      setSelectedRecord(null);
                      loadDashboard();
                      loadRecords();
                    }
                  }}
                >
                  Flag Suspicious
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}