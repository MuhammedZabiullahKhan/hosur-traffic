// ============================================================
// HOSUR TRAFFIC CONTROL CENTER - MAIN
// Created by Shri Muhammed Zabiullah Khan @Axion_Z_Squad
// ============================================================

const API_BASE = 'https://hosur-traffic.onrender.com/api';
let currentData = null;
let updateInterval = null;
let audioCtx = null;

// ---------- SOUND EFFECTS ----------
function playSound(type) {
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        if (type === 'alert') {
            oscillator.frequency.value = 800;
            gainNode.gain.value = 0.1;
            oscillator.start();
            setTimeout(() => oscillator.stop(), 200);
        } else if (type === 'update') {
            oscillator.frequency.value = 600;
            gainNode.gain.value = 0.05;
            oscillator.start();
            setTimeout(() => oscillator.stop(), 100);
        }
    } catch (e) { /* Silently fail if audio not supported */ }
}

// ---------- DOM REFS ----------
const elements = {
    updateTime: document.getElementById('updateTime'),
    statusTitle: document.getElementById('statusTitle'),
    statusDescription: document.getElementById('statusDescription'),
    probText: document.getElementById('probText'),
    ringFill: document.getElementById('ringFill'),
    confidenceText: document.getElementById('confidenceText'),
    confidenceBadge: document.getElementById('confidenceBadge'),
    dataFreshness: document.getElementById('dataFreshness'),
    historyCount: document.getElementById('historyCount'),
    redLight: document.getElementById('redLight'),
    yellowLight: document.getElementById('yellowLight'),
    greenLight: document.getElementById('greenLight'),
    liveDot: document.getElementById('liveDot'),
    liveStatus: document.getElementById('liveStatus'),
    methodsGrid: document.getElementById('methodsGrid'),
    locationsGrid: document.getElementById('locationsGrid'),
    statusCard: document.getElementById('statusCard')
};

// Pollutant element IDs
const pollutantIds = {
    no2: { value: 'no2Value', bar: 'no2Bar' },
    pm25: { value: 'pm25Value', bar: 'pm25Bar' },
    pm10: { value: 'pm10Value', bar: 'pm10Bar' },
    co: { value: 'coValue', bar: 'coBar' },
    temp: { value: 'tempValue', bar: null },
    humid: { value: 'humidValue', bar: null },
    wind: { value: 'windValue', bar: null },
    pressure: { value: 'pressureValue', bar: null }
};

const MAX_VALUES = { no2: 60, pm25: 150, pm10: 100, co: 10 };

// ---------- FLOW CATEGORIES (Professional Display) ----------
const flowCategories = {
    'Bayesian + Historical': {
        icon: '📊',
        label: 'Historical Pattern',
        color: '#667eea',
        getStatus: (prob) => {
            if (prob < 0.2) return 'Clear Flow';
            if (prob < 0.4) return 'Light Flow';
            if (prob < 0.6) return 'Building Flow';
            if (prob < 0.8) return 'Dense Flow';
            return 'Gridlock';
        },
        getDescription: (prob) => {
            if (prob < 0.2) return 'Below average congestion';
            if (prob < 0.4) return 'Normal for this time';
            if (prob < 0.6) return 'Above typical levels';
            if (prob < 0.8) return 'Peak period flow';
            return 'Historical high';
        }
    },
    'Physics-Based PSI': {
        icon: '🌤️',
        label: 'Atmospheric Analysis',
        color: '#4ade80',
        getStatus: (prob) => {
            if (prob < 0.2) return 'Free Flow';
            if (prob < 0.4) return 'Light Flow';
            if (prob < 0.6) return 'Moderate Flow';
            if (prob < 0.8) return 'Heavy Flow';
            return 'Stop & Go';
        },
        getDescription: (prob) => {
            if (prob < 0.2) return 'Optimal conditions';
            if (prob < 0.4) return 'Good flow maintained';
            if (prob < 0.6) return 'Flow is building';
            if (prob < 0.8) return 'Flow is restricted';
            return 'Severe restriction';
        }
    },
    'Time-Series Forecast': {
        icon: '📈',
        label: 'Trend Analysis',
        color: '#facc15',
        getStatus: (prob) => {
            if (prob < 0.2) return 'Below Average';
            if (prob < 0.4) return 'Typical';
            if (prob < 0.6) return 'Above Average';
            if (prob < 0.8) return 'Peak';
            return 'Record High';
        },
        getDescription: (prob) => {
            if (prob < 0.2) return 'Unusually light';
            if (prob < 0.4) return 'Matches patterns';
            if (prob < 0.6) return 'Higher than normal';
            if (prob < 0.8) return 'Near peak levels';
            return 'Historic levels';
        }
    },
    'Ensemble + Physics': {
        icon: '🎯',
        label: 'Integrated Analysis',
        color: '#f093fb',
        getStatus: (prob) => {
            if (prob < 0.2) return 'Clear';
            if (prob < 0.4) return 'Light';
            if (prob < 0.6) return 'Moderate';
            if (prob < 0.8) return 'Heavy';
            return 'Severe';
        },
        getDescription: (prob) => {
            if (prob < 0.2) return 'Free movement';
            if (prob < 0.4) return 'Smooth flow';
            if (prob < 0.6) return 'Flow building';
            if (prob < 0.8) return 'Flow dense';
            return 'Flow restricted';
        }
    },
    // Fallback for any other method names
    'default': {
        icon: '📊',
        label: 'Analysis',
        color: '#888',
        getStatus: (prob) => {
            if (prob < 0.2) return 'Low';
            if (prob < 0.4) return 'Medium';
            if (prob < 0.6) return 'Moderate';
            if (prob < 0.8) return 'High';
            return 'Very High';
        },
        getDescription: (prob) => {
            if (prob < 0.2) return 'Below normal';
            if (prob < 0.4) return 'Within range';
            if (prob < 0.6) return 'Above normal';
            if (prob < 0.8) return 'Elevated';
            return 'Extreme';
        }
    }
};

// ---------- FETCH DATA ----------
async function fetchTrafficData() {
    try {
        const response = await fetch(`${API_BASE}/traffic`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        currentData = data;
        updateUI(data);
        playSound('update');
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
        showError(error.message);
        return null;
    }
}

// ---------- UPDATE UI ----------
function updateUI(data) {
    const time = new Date(data.timestamp);
    elements.updateTime.textContent = time.toLocaleString();

    const prob = data.final_probability / 100;
    const probPercent = (prob * 100).toFixed(1);

    // Ring
    const circumference = 2 * Math.PI * 50;
    const offset = circumference - (prob * circumference);
    elements.ringFill.style.strokeDasharray = circumference;
    elements.ringFill.style.strokeDashoffset = offset;
    elements.probText.textContent = `${probPercent}%`;

    // Status
    elements.statusTitle.textContent = data.traffic_status || 'Unknown';
    elements.statusDescription.textContent = data.description || '';

    // ----- BEACON LIGHTS -----
    // Reset all lights
    elements.redLight.className = 'beacon-light';
    elements.yellowLight.className = 'beacon-light';
    elements.greenLight.className = 'beacon-light';

    if (prob < 0.3) {
        elements.greenLight.classList.add('active-green');
    } else if (prob < 0.6) {
        elements.yellowLight.classList.add('active-yellow');
    } else {
        elements.redLight.classList.add('active-red');
    }

    // Confidence
    const conf = data.confidence || 'Medium';
    elements.confidenceText.textContent = conf;
    elements.confidenceText.className = conf.toLowerCase();

    // LED
    elements.liveDot.className = 'led-dot active';
    elements.liveStatus.textContent = 'LIVE';

    // Freshness
    elements.dataFreshness.textContent = `📡 Data: ${data.data_freshness || 'Unknown'}`;
    elements.historyCount.textContent = `📊 Records: ${data.total_history_records || 0}`;

    // Pollutants
    if (data.station_data) {
        const sd = data.station_data;
        for (const [key, ids] of Object.entries(pollutantIds)) {
            const value = sd[key];
            if (value !== undefined) {
                const el = document.getElementById(ids.value);
                if (el) el.textContent = typeof value === 'number' ? value.toFixed(1) : '--';

                if (ids.bar) {
                    const bar = document.getElementById(ids.bar);
                    if (bar && typeof value === 'number') {
                        const max = MAX_VALUES[key] || 100;
                        const pct = Math.min(100, (value / max) * 100);
                        bar.style.width = `${pct}%`;
                        bar.style.background = pct < 40 ? '#4ade80' : pct < 70 ? '#facc15' : '#f87171';
                    }
                }
            }
        }
    }

    // Methods & Locations
    renderMethods(data.methods || []);
    renderLocations(data.locations || []);
}

// ---------- RENDER METHODS (Professional - Hides Raw Percentages) ----------
function renderMethods(methods) {
    elements.methodsGrid.innerHTML = methods.map(m => {
        // Get flow category for this method
        const flow = flowCategories[m.method] || flowCategories['default'];
        const status = flow.getStatus(m.probability);
        const description = flow.getDescription(m.probability);
        const confClass = m.confidence?.toLowerCase() || 'medium';
        const probPercent = (m.probability * 100).toFixed(1);
        
        return `
            <div class="method-card">
                <div class="method-name">
                    <span style="color:${flow.color}">${flow.icon}</span> 
                    ${flow.label}
                </div>
                <div class="method-prob" style="color:${flow.color}">
                    ${status}
                </div>
                <div class="method-desc" style="font-size:0.7rem;color:#888;margin:2px 0;">
                    ${description}
                </div>
                <div class="method-conf ${confClass}">
                    ● ${m.confidence || 'Medium'} Confidence
                </div>
            </div>
        `;
    }).join('');
}

// ---------- RENDER LOCATIONS ----------
function renderLocations(locations) {
    elements.locationsGrid.innerHTML = locations.map(l => {
        const prob = (l.probability * 100).toFixed(1);
        const peak = l.peak_hour ? '🔺 Peak' : '⏳ Off-peak';
        const weekend = l.weekend ? '📅 Weekend' : '📆 Weekday';
        
        // Flow status for location
        let flowStatus = 'Light';
        if (l.probability < 0.2) flowStatus = 'Clear';
        else if (l.probability < 0.4) flowStatus = 'Light';
        else if (l.probability < 0.6) flowStatus = 'Moderate';
        else if (l.probability < 0.8) flowStatus = 'Heavy';
        else flowStatus = 'Severe';
        
        return `
            <div class="location-card">
                <div class="loc-name">${l.location}</div>
                <div class="loc-prob">${flowStatus} Flow</div>
                <div class="loc-detail">${peak} · ${weekend}</div>
                <div class="loc-detail">${l.trend || 'Stable'} · ${l.confidence || 'Medium'}</div>
            </div>
        `;
    }).join('');
}

// ---------- ERROR ----------
function showError(message) {
    elements.statusCard.classList.add('error');
    elements.statusTitle.textContent = '⚠️ Error';
    elements.statusDescription.textContent = message || 'Failed to fetch data';
    elements.probText.textContent = '--%';
    elements.liveDot.className = 'led-dot inactive';
    elements.liveStatus.textContent = 'OFFLINE';
    playSound('alert');
}

// ---------- AUTO REFRESH ----------
function startAutoRefresh(interval = 30000) {
    if (updateInterval) clearInterval(updateInterval);
    updateInterval = setInterval(fetchTrafficData, interval);
}

// ---------- GRADIENT DEF ----------
function addGradientDef() {
    const svg = document.querySelector('.probability-ring svg');
    if (svg) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const grad = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        grad.id = 'grad';
        grad.setAttribute('x1', '0%');
        grad.setAttribute('y1', '0%');
        grad.setAttribute('x2', '100%');
        grad.setAttribute('y2', '100%');

        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('style', 'stop-color:#667eea;stop-opacity:1');

        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('style', 'stop-color:#764ba2;stop-opacity:1');

        grad.appendChild(stop1);
        grad.appendChild(stop2);
        defs.appendChild(grad);
        svg.appendChild(defs);
    }
}

// ---------- INIT ----------
async function init() {
    addGradientDef();
    await fetchTrafficData();
    startAutoRefresh(60000);
}

document.addEventListener('DOMContentLoaded', init);
