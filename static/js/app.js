// LifeCode AI — Frontend JavaScript
// Flask REST API connection | Sensor polling | Groq AI results

const API = '';  // same origin

// ── State ─────────────────────────────────────────────────────────────────
let medicalData  = { glucose: 95, cholesterol: 180, hemoglobin: 13.5 };
let capturedHR   = null;
let sensorPollTimer = null;

// ── Initialization ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkSensorStatus();
  sensorPollTimer = setInterval(checkSensorStatus, 5000); // poll every 5s
});

// ── Tab Switching ──────────────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(name + '-tab').classList.add('active');
}

// ── Slider Utility ─────────────────────────────────────────────────────────
function updateSlider(id, displayId, formatter) {
  const val = parseFloat(document.getElementById(id).value);
  document.getElementById(displayId).textContent = formatter(val);
}

// ── Logout ─────────────────────────────────────────────────────────────────
async function logout() {
  await fetch(`${API}/api/logout`, { method: 'POST' });
  window.location.href = '/login';
}

// ── Sensor Polling ─────────────────────────────────────────────────────────
async function checkSensorStatus() {
  try {
    const res  = await fetch(`${API}/api/sensor-status`);
    if (!res.ok) return;
    const data = await res.json();

    const isPhysical = data.is_physical;
    const badge      = document.getElementById('sensorBadge');
    const dot        = document.getElementById('badgeDot');
    const text       = document.getElementById('badgeText');
    const bar        = document.getElementById('sensorBar');

    if (isPhysical) {
      dot.classList.add('online');
      text.textContent = '● Physical Mode (ESP32)';
      badge.style.borderColor = 'rgba(16,185,129,0.4)';
      bar.style.display = 'flex';

      if (data.data) {
        document.getElementById('liveHR').textContent   = data.data.heart_rate;
        document.getElementById('liveGSR').textContent  = data.data.gsr;
        document.getElementById('liveTemp').textContent = data.data.temperature;
      }

      updateSensorTab(isPhysical, data.data);
    } else {
      dot.classList.remove('online');
      text.textContent = '● Virtual Mode';
      badge.style.borderColor = '';
      bar.style.display = 'none';
      updateSensorTab(false, null);
    }
  } catch (e) {
    // Silent fail — no crash
  }
}

async function refreshSensor() {
  await checkSensorStatus();

  const stress   = parseInt(document.getElementById('stress')?.value   || 5);
  const activity = parseFloat(document.getElementById('activity')?.value || 3);

  try {
    const res  = await fetch(`${API}/api/live-sensor?stress=${stress}&activity=${activity}`);
    const data = await res.json();
    if (data.success && data.sensor) {
      document.getElementById('sm-hr').textContent   = data.sensor.heart_rate + ' BPM';
      document.getElementById('sm-gsr').textContent  = data.sensor.gsr + ' µS';
      document.getElementById('sm-temp').textContent = data.sensor.temperature + ' °C';
      document.getElementById('sensorTimestamp').textContent =
        'Last updated: ' + (data.sensor.timestamp || new Date().toLocaleTimeString());
    }
  } catch (e) { /* silent */ }
}

function updateSensorTab(isPhysical, sensorData) {
  const statusBig = document.getElementById('sensorStatusBig');
  if (!statusBig) return;

  if (isPhysical && sensorData) {
    statusBig.innerHTML = `
      <div class="status-icon">🟢</div>
      <div class="status-text">ESP32 Connected</div>
      <div class="status-sub">Receiving live data every 1 second</div>`;
    document.getElementById('sm-hr').textContent   = sensorData.heart_rate + ' BPM';
    document.getElementById('sm-gsr').textContent  = sensorData.gsr + ' µS';
    document.getElementById('sm-temp').textContent = sensorData.temperature + ' °C';
    document.getElementById('sensorTimestamp').textContent =
      'Last updated: ' + (sensorData.timestamp || new Date().toLocaleTimeString());
  } else {
    statusBig.innerHTML = `
      <div class="status-icon">🔴</div>
      <div class="status-text">No Hardware Detected</div>
      <div class="status-sub">Connect ESP32 via USB cable</div>`;
  }
}

// ── Report Upload ──────────────────────────────────────────────────────────
async function uploadReport(event) {
  const file = event.target.files[0];
  if (!file) return;
  const drop = document.getElementById('fileDrop');
  drop.innerHTML = '<div class="file-drop-icon">🔍</div><p>Processing...</p>';

  try {
    const form = new FormData();
    form.append('report', file);
    const res  = await fetch(`${API}/api/upload-report`, { method: 'POST', body: form });
    const data = await res.json();

    if (data.success) {
      medicalData = data.data;
      document.getElementById('d-glucose').textContent = data.data.glucose;
      document.getElementById('d-chol').textContent    = data.data.cholesterol;
      document.getElementById('d-hemo').textContent    = data.data.hemoglobin;
      document.getElementById('reportResult').style.display = 'block';
      drop.innerHTML = '<div class="file-drop-icon">✅</div><p>Report uploaded!</p><small>Click to replace</small>';
    } else {
      throw new Error(data.error);
    }
  } catch (e) {
    alert('❌ Upload failed: ' + e.message);
    drop.innerHTML = '<div class="file-drop-icon">📂</div><p>Click or drag a report here</p><small>PDF • JPG • PNG</small>';
  }
}

// ── Camera Scan ────────────────────────────────────────────────────────────
async function startCamera() {
  const btn = event.target;
  btn.textContent = '📸 Scanning...';
  btn.disabled    = true;

  try {
    const res  = await fetch(`${API}/api/camera-scan`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ duration: 3 })
    });
    const data = await res.json();
    if (data.success) {
      capturedHR = data.heart_rate;
      document.getElementById('cameraHR').textContent              = capturedHR;
      document.getElementById('cameraResult').style.display        = 'block';
      btn.textContent = '✅ Captured';
    } else throw new Error(data.error);
  } catch (e) {
    alert('❌ Scan failed: ' + e.message);
    btn.textContent = '🎥 Start Camera Scan';
  } finally {
    btn.disabled = false;
  }
}

// ── Display Results ────────────────────────────────────────────────────────
function showResults(predictions, sensor, aiText) {
  const section = document.getElementById('results');
  section.classList.add('active');

  // Scores
  document.getElementById('r-stress').textContent    = predictions.stress_index;
  document.getElementById('r-metabolic').textContent = predictions.metabolic_score;
  document.getElementById('r-risk').textContent      = predictions.lifestyle_risk;

  // Badges
  setBadge('r-stress-badge',    predictions.stress_index,    false);
  setBadge('r-metabolic-badge', predictions.metabolic_score, true);
  setBadge('r-risk-badge',      predictions.lifestyle_risk,  false);

  // Sensor strip
  if (sensor) {
    document.getElementById('sensorStrip').innerHTML =
      `<span>🔌 Sensor Mode: <strong>${sensor.is_virtual ? 'Virtual Estimate' : '🟢 Physical ESP32'}</strong></span>
       <span>❤️ HR: <strong>${sensor.heart_rate} BPM</strong></span>
       <span>⚡ GSR: <strong>${sensor.gsr} µS</strong></span>
       <span>🌡️ Temp: <strong>${sensor.temperature}°C</strong></span>`;
  }

  // AI Insights
  if (aiText) {
    document.getElementById('aiContent').innerHTML = mdToHTML(aiText);
  }

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setBadge(id, val, higherIsBetter) {
  const el  = document.getElementById(id);
  const
