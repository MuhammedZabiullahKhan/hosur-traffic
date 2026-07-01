#!/usr/bin/env python3
"""
ADVANCED HOSUR TRAFFIC PROBABILITY SYSTEM v3.0
Created by Shri Muhammed Zabiullah Khan @Axion_Z_Squad

Combines: Past Data + Real-time AQI + Statistical Methods + Physics PSI
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_caching import Cache
import requests
import json
import math
import numpy as np
from datetime import datetime, timedelta
import os
import pickle
from collections import defaultdict
from scipy import stats
from scipy.optimize import curve_fit

app = Flask(__name__)
CORS(app)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

# ======================
# CONFIGURATION
# ======================

AQI_API_TOKEN = os.environ.get('AQI_API_TOKEN', 'bd175968d7b797e5b2152c4291a1b498a786e26b')
HOSUR_STATION_ID = "14147"
VERSION = "3.0.0"
CREATOR = "Shri Muhammed Zabiullah Khan"
TEAM = "@Axion_Z_Squad"

# ======================
# HISTORICAL DATA STORE
# ======================

class HistoricalDataStore:
    """Store and manage historical traffic data"""
    
    def __init__(self):
        self.data_file = 'traffic_history.pkl'
        self.history = self.load_history()
        self.daily_patterns = self.calculate_daily_patterns()
    
    def load_history(self):
        """Load historical data from file"""
        try:
            with open(self.data_file, 'rb') as f:
                return pickle.load(f)
        except:
            return defaultdict(list)
    
    def save_history(self):
        """Save historical data to file"""
        try:
            with open(self.data_file, 'wb') as f:
                pickle.dump(self.history, f)
        except:
            pass
    
    def add_record(self, no2, pm25, co, temperature, humidity, pressure, 
                   traffic_prob, status, location):
        """Add a new record to history"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'no2': no2,
            'pm25': pm25,
            'co': co,
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'traffic_prob': traffic_prob,
            'status': status,
            'location': location,
            'hour': datetime.now().hour,
            'day': datetime.now().weekday(),
            'is_weekend': datetime.now().weekday() >= 5
        }
        
        key = f"{location}_{datetime.now().strftime('%Y-%m-%d')}"
        self.history[key].append(record)
        self.save_history()
        return record
    
    def calculate_daily_patterns(self):
        """Calculate average patterns for each hour"""
        patterns = defaultdict(lambda: defaultdict(list))
        
        for key, records in self.history.items():
            for record in records:
                hour = record['hour']
                is_weekend = record['is_weekend']
                location = record['location']
                
                patterns[location][f"{'weekend' if is_weekend else 'weekday'}_{hour}"].append({
                    'no2': record['no2'],
                    'traffic_prob': record['traffic_prob']
                })
        
        daily_patterns = {}
        for location, pattern in patterns.items():
            daily_patterns[location] = {}
            for key, values in pattern.items():
                if values:
                    avg_no2 = np.mean([v['no2'] for v in values])
                    avg_prob = np.mean([v['traffic_prob'] for v in values])
                    daily_patterns[location][key] = {
                        'avg_no2': avg_no2,
                        'avg_prob': avg_prob,
                        'count': len(values),
                        'std_no2': np.std([v['no2'] for v in values]) if len(values) > 1 else 0,
                        'std_prob': np.std([v['traffic_prob'] for v in values]) if len(values) > 1 else 0
                    }
        
        return daily_patterns
    
    def get_historical_prediction(self, location, current_hour, is_weekend):
        """Get historical prediction based on past data"""
        key = f"{'weekend' if is_weekend else 'weekday'}_{current_hour}"
        
        if location in self.daily_patterns and key in self.daily_patterns[location]:
            data = self.daily_patterns[location][key]
            return {
                'expected_no2': data['avg_no2'],
                'expected_prob': data['avg_prob'],
                'confidence': 'High' if data['count'] > 10 else 'Medium' if data['count'] > 5 else 'Low',
                'sample_count': data['count'],
                'std_dev': data['std_no2']
            }
        return None

# ======================
# ADVANCED PSI CALCULATOR (PHYSICS-BASED)
# ======================

class PhysicsPSI:
    """Physics-based Pollutant Standard Index using gas laws"""
    
    def __init__(self, no2, pm25, co, temperature, humidity, pressure, wind):
        self.no2 = no2
        self.pm25 = pm25
        self.co = co
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        self.wind = wind
        
        self.R = 8.314
        self.T_ref = 298.15
        self.P_ref = 1013.25
    
    def calculate_density(self):
        T_kelvin = self.temperature + 273.15
        return (self.pressure * 100) / (self.R * T_kelvin)
    
    def calculate_psi_physics(self):
        def base_psi(value, pollutant_type):
            psi_ranges = {
                'no2': [(0, 20, 0, 50), (20, 40, 50, 100), (40, 80, 100, 200), 
                        (80, 120, 200, 300), (120, 200, 300, 500)],
                'pm25': [(0, 15, 0, 50), (15, 30, 50, 100), (30, 65, 100, 200),
                         (65, 100, 200, 300), (100, 200, 300, 500)],
                'co': [(0, 1, 0, 50), (1, 3, 50, 100), (3, 6, 100, 200),
                       (6, 10, 200, 300), (10, 20, 300, 500)]
            }
            ranges = psi_ranges.get(pollutant_type, psi_ranges['no2'])
            for low, high, psi_low, psi_high in ranges:
                if low <= value < high:
                    return psi_low + (value - low) * (psi_high - psi_low) / (high - low)
            return 500 if value >= ranges[-1][1] else 0
        
        T_factor = 1 + 0.01 * (self.temperature - 25)
        P_factor = 1 + 0.005 * (1013.25 - self.pressure) / 100
        H_factor = 1 + 0.005 * (self.humidity - 60)
        W_factor = 1 / (1 + 0.1 * self.wind)
        
        no2_psi = base_psi(self.no2, 'no2') * T_factor * P_factor * W_factor
        pm25_psi = base_psi(self.pm25, 'pm25') * H_factor * W_factor
        co_psi = base_psi(self.co, 'co') * T_factor * W_factor
        
        if self.wind > 3:
            weights = {'no2': 0.3, 'pm25': 0.3, 'co': 0.4}
        elif self.humidity > 70:
            weights = {'no2': 0.4, 'pm25': 0.4, 'co': 0.2}
        else:
            weights = {'no2': 0.5, 'pm25': 0.3, 'co': 0.2}
        
        psi = no2_psi * weights['no2'] + pm25_psi * weights['pm25'] + co_psi * weights['co']
        prob = 0.1 + 0.8 / (1 + math.exp(-(psi - 100) / 40))
        
        return {
            'psi': psi,
            'probability': prob,
            'physics_factors': {
                'temperature_factor': T_factor,
                'pressure_factor': P_factor,
                'humidity_factor': H_factor,
                'wind_factor': W_factor,
                'air_density': self.calculate_density()
            },
            'pollutant_contributions': {
                'no2': no2_psi,
                'pm25': pm25_psi,
                'co': co_psi
            }
        }

# ======================
# ADVANCED TRAFFIC ANALYZER
# ======================

class AdvancedTrafficAnalyzer:
    """Combines historical data, real-time AQI, and advanced statistics"""
    
    def __init__(self, station_data, historical_store):
        self.data = station_data
        self.historical = historical_store
        self.no2 = station_data.get('no2', 0)
        self.pm25 = station_data.get('pm25', 0)
        self.pm10 = station_data.get('pm10', 0)
        self.co = station_data.get('co', 0)
        self.temp = station_data.get('temperature', 25)
        self.humidity = station_data.get('humidity', 60)
        self.pressure = station_data.get('pressure', 1013)
        self.wind = station_data.get('wind', 0)
        
        self.current_hour = datetime.now().hour
        self.is_weekend = datetime.now().weekday() >= 5
        
        self.historical_avg = {
            'no2': 18.5,
            'no2_lockdown': 4.2,
            'pm25': 52.0,
            'pm10': 35.0
        }
    
    def bayesian_with_history(self):
        """Bayesian probability using historical data as prior"""
        historical_pred = self.historical.get_historical_prediction(
            'SIPCOT Phase-1, Hosur', 
            self.current_hour, 
            self.is_weekend
        )
        
        if historical_pred:
            prior = historical_pred['expected_prob']
            prior_weight = min(0.7, 0.3 + 0.04 * historical_pred['sample_count'])
        else:
            if 8 <= self.current_hour <= 10 or 17 <= self.current_hour <= 19:
                prior = 0.7
            elif 11 <= self.current_hour <= 16:
                prior = 0.45
            else:
                prior = 0.2
            prior_weight = 0.4
        
        no2_likelihood = 1 / (1 + math.exp(-(self.no2 - 25) / 10))
        pm25_likelihood = 1 / (1 + math.exp(-(self.pm25 - 50) / 20))
        likelihood = (no2_likelihood * 0.6 + pm25_likelihood * 0.4)
        
        posterior = (likelihood * prior * prior_weight) / (
            likelihood * prior * prior_weight + 
            (1 - likelihood) * (1 - prior) * (1 - prior_weight) + 0.001
        )
        
        return {
            'method': 'Bayesian + Historical',
            'probability': min(max(posterior, 0), 1),
            'prior': prior,
            'prior_weight': prior_weight,
            'likelihood': likelihood,
            'historical_sample_count': historical_pred['sample_count'] if historical_pred else 0,
            'confidence': 'High' if posterior > 0.7 else 'Medium' if posterior > 0.4 else 'Low'
        }
    
    def physics_psi_method(self):
        """PSI calculation with physics adjustments"""
        psi_calc = PhysicsPSI(
            self.no2, self.pm25, self.co,
            self.temp, self.humidity, self.pressure, self.wind
        )
        result = psi_calc.calculate_psi_physics()
        
        return {
            'method': 'Physics-Based PSI',
            'probability': result['probability'],
            'psi_value': result['psi'],
            'physics_factors': result['physics_factors'],
            'pollutant_contributions': result['pollutant_contributions'],
            'confidence': 'High' if result['psi'] > 100 else 'Medium' if result['psi'] > 50 else 'Low'
        }
    
    def time_series_forecast(self):
        """Predict traffic using time-series analysis"""
        historical_pred = self.historical.get_historical_prediction(
            'SIPCOT Phase-1, Hosur',
            self.current_hour,
            self.is_weekend
        )
        
        if historical_pred and historical_pred['sample_count'] > 3:
            base_prob = historical_pred['expected_prob']
            no2_deviation = self.no2 - historical_pred['expected_no2']
            adjustment = 0.2 * (no2_deviation / 10)
            prob = min(1, max(0, base_prob + adjustment))
            
            return {
                'method': 'Time-Series Forecast',
                'probability': prob,
                'base_probability': base_prob,
                'deviation': no2_deviation,
                'adjustment': adjustment,
                'sample_count': historical_pred['sample_count'],
                'confidence': 'High' if historical_pred['sample_count'] > 10 else 'Medium'
            }
        else:
            if 8 <= self.current_hour <= 10 or 17 <= self.current_hour <= 19:
                prob = 0.6 + 0.2 * (self.no2 / 30)
            elif 11 <= self.current_hour <= 16:
                prob = 0.4 + 0.2 * (self.no2 / 30)
            else:
                prob = 0.2 + 0.2 * (self.no2 / 30)
            
            return {
                'method': 'Time-Series Forecast (Limited Data)',
                'probability': min(1, max(0, prob)),
                'sample_count': 0,
                'confidence': 'Low'
            }
    
    def ensemble_with_physics(self):
        """Combine all methods with physics-based weighting"""
        bayesian = self.bayesian_with_history()
        physics_psi = self.physics_psi_method()
        timeseries = self.time_series_forecast()
        
        weights = {'bayesian': 0.30, 'physics': 0.35, 'timeseries': 0.35}
        
        if bayesian['confidence'] == 'High':
            weights['bayesian'] += 0.05
        if physics_psi['confidence'] == 'High':
            weights['physics'] += 0.05
        if timeseries['confidence'] == 'High':
            weights['timeseries'] += 0.05
        
        total = sum(weights.values())
        for key in weights:
            weights[key] /= total
        
        ensemble_prob = (
            bayesian['probability'] * weights['bayesian'] +
            physics_psi['probability'] * weights['physics'] +
            timeseries['probability'] * weights['timeseries']
        )
        
        if self.wind > 5:
            ensemble_prob *= 0.85
        if self.humidity > 80:
            ensemble_prob *= 1.05
        
        ensemble_prob = min(1, max(0, ensemble_prob))
        
        return {
            'method': 'Ensemble + Physics',
            'probability': ensemble_prob,
            'weights': weights,
            'individual_results': {
                'bayesian': bayesian['probability'],
                'physics_psi': physics_psi['probability'],
                'timeseries': timeseries['probability']
            },
            'wind_adjustment': 0.85 if self.wind > 5 else 1.0,
            'humidity_adjustment': 1.05 if self.humidity > 80 else 1.0,
            'confidence': 'High' if ensemble_prob > 0.6 else 'Medium' if ensemble_prob > 0.3 else 'Low'
        }
    
    def location_with_history(self, location_name):
        """Location-specific probability with historical data"""
        ensemble = self.ensemble_with_physics()
        base_prob = ensemble['probability']
        
        location_factors = {
            'Hosur Bus Stand': {
                'peak_factor': 1.35,
                'weekend_factor': 0.75,
                'adj_factor': 0.2,
                'historical_delta': 0.15,
                'description': 'High pedestrian + vehicle traffic'
            },
            'SIPCOT Industrial Area': {
                'peak_factor': 1.2,
                'weekend_factor': 0.5,
                'adj_factor': 0.15,
                'historical_delta': 0.1,
                'description': 'Industrial + heavy vehicle traffic'
            },
            'Hosur-Bangalore Highway': {
                'peak_factor': 1.5,
                'weekend_factor': 0.85,
                'adj_factor': 0.3,
                'historical_delta': 0.2,
                'description': 'Major inter-city corridor'
            },
            'Hosur City Center': {
                'peak_factor': 1.3,
                'weekend_factor': 1.1,
                'adj_factor': 0.15,
                'historical_delta': 0.1,
                'description': 'Mixed commercial + residential'
            }
        }
        
        factors = location_factors.get(location_name, {
            'peak_factor': 1.0,
            'weekend_factor': 1.0,
            'adj_factor': 0.0,
            'historical_delta': 0.0,
            'description': 'Standard location'
        })
        
        historical_pred = self.historical.get_historical_prediction(
            location_name,
            self.current_hour,
            self.is_weekend
        )
        
        adjusted_prob = base_prob
        
        if self.is_weekend:
            adjusted_prob *= factors['weekend_factor']
        else:
            if (7 <= self.current_hour <= 10) or (16 <= self.current_hour <= 19):
                adjusted_prob *= factors['peak_factor']
        
        adjusted_prob += factors['adj_factor']
        
        if historical_pred and historical_pred['sample_count'] > 5:
            historical_correction = historical_pred['expected_prob'] * 0.1
            adjusted_prob += historical_correction
        
        adjusted_prob = max(0, min(1, adjusted_prob))
        
        if historical_pred and historical_pred['sample_count'] > 3:
            no2_trend = self.no2 / historical_pred['expected_no2'] if historical_pred['expected_no2'] > 0 else 1
            trend = 'Increasing' if no2_trend > 1.1 else 'Decreasing' if no2_trend < 0.9 else 'Stable'
        else:
            trend = 'Unknown (Insufficient data)'
        
        return {
            'location': location_name,
            'probability': adjusted_prob,
            'base_probability': base_prob,
            'historical_delta': factors['historical_delta'],
            'peak_hour': (7 <= self.current_hour <= 10) or (16 <= self.current_hour <= 19),
            'weekend': self.is_weekend,
            'trend': trend,
            'sample_count': historical_pred['sample_count'] if historical_pred else 0,
            'description': factors['description'],
            'confidence': 'High' if adjusted_prob > 0.6 else 'Medium'
        }
    
    def complete_analysis(self):
        """Run all methods and return comprehensive analysis"""
        bayesian = self.bayesian_with_history()
        physics_psi = self.physics_psi_method()
        timeseries = self.time_series_forecast()
        ensemble = self.ensemble_with_physics()
        
        locations = ['Hosur Bus Stand', 'SIPCOT Industrial Area', 
                     'Hosur-Bangalore Highway', 'Hosur City Center']
        location_results = [self.location_with_history(loc) for loc in locations]
        
        final_prob = ensemble['probability']
        
        if final_prob < 0.15:
            status = "VERY LIGHT TRAFFIC"
            icon = "🟢"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        elif final_prob < 0.30:
            status = "LIGHT TRAFFIC"
            icon = "🟢"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        elif final_prob < 0.50:
            status = "MODERATE TRAFFIC"
            icon = "🟡"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        elif final_prob < 0.70:
            status = "HEAVY TRAFFIC"
            icon = "🟠"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        elif final_prob < 0.85:
            status = "VERY HEAVY TRAFFIC"
            icon = "🔴"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        else:
            status = "EXTREME TRAFFIC"
            icon = "🚨"
            desc = f"NO₂: {self.no2:.1f} µg/m³ | Wind: {self.wind:.1f} m/s"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'station_data': self.data,
            'methods': [bayesian, physics_psi, timeseries, ensemble],
            'locations': location_results,
            'final_probability': final_prob * 100,
            'traffic_status': status,
            'status_icon': icon,
            'description': desc,
            'confidence': ensemble['confidence'],
            'historical_data_available': len(self.historical.history) > 0,
            'total_history_records': len(self.historical.history),
            'version': VERSION,
            'creator': CREATOR,
            'team': TEAM
        }

# ======================
# DATA FETCHING
# ======================

@cache.memoize(timeout=300)
def fetch_station_data_cached(station_id):
    """Fetch air quality data with caching"""
    url = f"https://api.waqi.info/feed/@{station_id}/?token={AQI_API_TOKEN}"
    try:
        response = requests.get(url, timeout=8)
        data = response.json()
        if data.get('status') == 'ok':
            station_data = data['data']
            iaqi = station_data.get('iaqi', {})
            return {
                'name': 'SIPCOT Phase-1, Hosur',
                'time': station_data.get('time', {}).get('s', 'N/A'),
                'no2': iaqi.get('no2', {}).get('v', 12.5),
                'pm25': iaqi.get('pm25', {}).get('v', 45.0),
                'pm10': iaqi.get('pm10', {}).get('v', 28.0),
                'co': iaqi.get('co', {}).get('v', 1.8),
                'so2': iaqi.get('so2', {}).get('v', 3.2),
                'o3': iaqi.get('o3', {}).get('v', 4.5),
                'temperature': iaqi.get('t', {}).get('v', 25.0),
                'humidity': iaqi.get('h', {}).get('v', 60.0),
                'pressure': iaqi.get('p', {}).get('v', 1013.0),
                'wind': iaqi.get('w', {}).get('v', 2.5)
            }
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# ======================
# ROUTES
# ======================

@app.route('/')
def index():
    return render_template('index.html', creator=CREATOR, team=TEAM, version=VERSION)

@app.route('/api/traffic')
def get_traffic_data():
    """Main API endpoint with advanced analysis"""
    station_data = fetch_station_data_cached(HOSUR_STATION_ID)
    if not station_data:
        return jsonify({'error': 'Failed to fetch data'}), 500
    
    historical_store = HistoricalDataStore()
    analyzer = AdvancedTrafficAnalyzer(station_data, historical_store)
    analysis = analyzer.complete_analysis()
    
    historical_store.add_record(
        no2=station_data.get('no2', 0),
        pm25=station_data.get('pm25', 0),
        co=station_data.get('co', 0),
        temperature=station_data.get('temperature', 25),
        humidity=station_data.get('humidity', 60),
        pressure=station_data.get('pressure', 1013),
        traffic_prob=analysis['final_probability'],
        status=analysis['traffic_status'],
        location='SIPCOT Phase-1, Hosur'
    )
    
    return jsonify(analysis)

@app.route('/api/history')
def get_history():
    """Get historical data summary"""
    historical_store = HistoricalDataStore()
    return jsonify({
        'total_records': len(historical_store.history),
        'daily_patterns': historical_store.daily_patterns,
        'latest_entries': list(historical_store.history.keys())[-10:] if historical_store.history else []
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'creator': CREATOR,
        'team': TEAM,
        'version': VERSION
    })

# ======================
# MAIN
# ======================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🏭 HOSUR TRAFFIC PROBABILITY SYSTEM v3.0")
    print("=" * 60)
    print(f"👤 Created by: {CREATOR}")
    print(f"🏷️  Team: {TEAM}")
    print(f"📦 Version: {VERSION}")
    print("=" * 60)
    print("🧪 Methods Used:")
    print("   • Bayesian + Historical Prior")
    print("   • Physics-Based PSI (Temperature, Pressure, Humidity, Wind)")
    print("   • Time-Series Forecast")
    print("   • Ensemble + Physics")
    print("   • Location-Specific with History")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
