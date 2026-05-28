import { useState, useEffect } from 'react';
import { getDataSources, ingestSAP, ingestUtility, ingestTravel } from '../services/api';
import './Import.css';

export default function Import() {
  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState('');
  const [selectedTenant] = useState('1');
  const [data, setData] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSources();
  }, [selectedTenant]);

  const loadSources = async () => {
    try {
      const response = await getDataSources(selectedTenant);
      setSources(response.data.results || []);
    } catch (err) {
      console.error('Failed to load sources:', err);
    }
  };

  const handleIngest = async () => {
    if (!selectedSource || !data) {
      setError('Please select a source and provide data');
      return;
    }

    setError('');
    setLoading(true);
    setResult(null);

    try {
      let parsedData;
      try {
        parsedData = JSON.parse(data);
        if (!Array.isArray(parsedData)) {
          parsedData = [parsedData];
        }
      } catch {
        // Try CSV parsing
        const lines = data.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        parsedData = lines.slice(1).map(line => {
          const values = line.split(',');
          const obj = {};
          headers.forEach((h, i) => {
            obj[h] = values[i]?.trim();
          });
          return obj;
        });
      }

      let response;
      const sourceType = sources.find(s => s.id === parseInt(selectedSource))?.source_type;

      switch (sourceType) {
        case 'sap':
          response = await ingestSAP(selectedTenant, selectedSource, parsedData);
          break;
        case 'utility':
          response = await ingestUtility(selectedTenant, selectedSource, parsedData);
          break;
        case 'travel':
          response = await ingestTravel(selectedTenant, selectedSource, parsedData);
          break;
        default:
          throw new Error('Unknown source type');
      }

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const sampleData = {
    sap: [
      { Material: 'Diesel Fuel', Plant: 'US01', Quantity: 5000, Unit: 'L', Date: '2025-01-15', Document: 'DOC001' },
      { Material: 'Natural Gas', Plant: 'US02', Quantity: 10000, Unit: 'm3', Date: '2025-01-20', Document: 'DOC002' }
    ],
    utility: [
      { account_number: 'ACCT001', meter_number: 'MTR001', billing_period_start: '2025-01-01', billing_period_end: '2025-01-31', kwh: 150000, tariff: 'industrial' },
      { account_number: 'ACCT002', meter_number: 'MTR002', billing_period_start: '2025-02-01', billing_period_end: '2025-02-28', kwh: 135000, tariff: 'commercial' }
    ],
    travel: [
      { trip_id: 'TRP001', trip_type: 'flight', traveler: 'John Smith', date: '2025-03-15', origin: 'JFK', destination: 'LAX', distance: 3983 },
      { trip_id: 'TRP002', trip_type: 'hotel', traveler: 'Jane Doe', date: '2025-03-16', origin: 'LAX', destination: 'SFO', distance: 615 }
    ]
  };

  const loadSample = () => {
    const sourceType = sources.find(s => s.id === parseInt(selectedSource))?.source_type;
    if (sourceType) {
      setData(JSON.stringify(sampleData[sourceType] || [], null, 2));
    }
  };

  return (
    <div className="import-page">
      <header className="import-header">
        <h1>Data Import</h1>
        <button onClick={() => window.location.href = '/dashboard'} className="btn-back">
          Back to Dashboard
        </button>
      </header>

      <div className="import-content">
        <div className="import-form">
          <div className="form-group">
            <label>Data Source</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
            >
              <option value="">Select a source...</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name} ({source.source_type_display})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>
              Data (JSON or CSV)
              {selectedSource && (
                <button
                  type="button"
                  className="btn-sample"
                  onClick={loadSample}
                >
                  Load Sample
                </button>
              )}
            </label>
            <textarea
              value={data}
              onChange={(e) => setData(e.target.value)}
              placeholder='[{"field": "value"}, ...]'
              rows={15}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            onClick={handleIngest}
            className="btn-import"
            disabled={loading || !selectedSource || !data}
          >
            {loading ? 'Importing...' : 'Import Data'}
          </button>
        </div>

        {result && (
          <div className="import-result">
            <h2>Import Results</h2>
            <div className="result-stats">
              <div className="result-stat">
                <span className="stat-label">Total Rows</span>
                <span className="stat-value">{result.total_rows}</span>
              </div>
              <div className="result-stat success">
                <span className="stat-label">Successful</span>
                <span className="stat-value">{result.success_count}</span>
              </div>
              <div className="result-stat error">
                <span className="stat-label">Failed</span>
                <span className="stat-value">{result.failed_count}</span>
              </div>
            </div>

            {result.errors?.length > 0 && (
              <div className="result-errors">
                <h3>Errors (showing first 10)</h3>
                {result.errors.map((err, idx) => (
                  <div key={idx} className="error-item">
                    Row {err.row}: {err.error}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}