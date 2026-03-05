import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [media, setMedia] = useState([]);
  const [section, setSection] = useState('Movies');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchMedia = async () => {
    try {
      const response = await fetch('/media');
      const data = await response.json();
      setMedia(data);
    } catch (err) {
      setError("Failed to fetch media data");
    }
  };

  const startScan = async () => {
    setLoading(true);
    try {
      await fetch(`/scan?section_name=${section}`, { method: 'POST' });
      alert("Scan started");
    } catch (err) { setError("Scan failed"); }
    setLoading(false);
  };

  const syncAll = async () => {
    try {
      await fetch(`/sync-all`, { method: 'POST' });
      alert("Mass sync started");
    } catch (err) { setError("Sync failed"); }
  };

  const syncItem = async (id) => {
    try {
      await fetch(`/sync/${id}`, { method: 'POST' });
    } catch (err) { setError("Sync failed"); }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Plex Thumbs</h1>
        <div className="controls">
          <input type="text" value={section} onChange={(e) => setSection(e.target.value)} />
          <button onClick={startScan} disabled={loading}>Scan Library</button>
          <button onClick={syncAll} className="sync-btn">Sync Everything</button>
        </div>
      </header>

      <main>
        {error && <div className="error">{error}</div>}
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Media Hash</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {media.map((item) => (
                <tr key={item.id}>
                  <td>{item.title}</td>
                  <td className="hash">{item.plex_hash}</td>
                  <td className={`status status-${item.sync_status}`}>
                    {item.sync_status.replace('_', ' ')}
                  </td>
                  <td>
                    <button className="small-btn" onClick={() => syncItem(item.id)}>Sync</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

export default App;
