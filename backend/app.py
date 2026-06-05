from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

UNITS = {
    "length": {
        "name": "长度",
        "units": {
            "千米": 1000, "米": 1, "厘米": 0.01, "毫米": 0.001,
            "微米": 1e-6, "纳米": 1e-9, "英里": 1609.344,
            "码": 0.9144, "英尺": 0.3048, "英寸": 0.0254, "海里": 1852
        }
    },
    "area": {
        "name": "面积",
        "units": {
            "平方公里": 1e6, "平方米": 1, "平方厘米": 1e-4,
            "平方毫米": 1e-6, "公顷": 1e4, "英亩": 4046.8564224,
            "平方英里": 2589988.110336, "平方英尺": 0.09290304
        }
    },
    "volume": {
        "name": "体积",
        "units": {
            "立方米": 1000, "立方厘米": 0.001, "升": 1, "毫升": 0.001,
            "加仑(美)": 3.785411784, "加仑(英)": 4.54609,
            "品脱(美)": 0.473176473, "夸脱(美)": 0.946352946,
            "立方英尺": 28.316846592
        }
    },
    "mass": {
        "name": "质量",
        "units": {
            "吨": 1000, "千克": 1, "克": 0.001, "毫克": 1e-6,
            "磅": 0.45359237, "盎司": 0.028349523125,
            "市斤": 0.5, "两": 0.05
        }
    },
    "time": {
        "name": "时间",
        "units": {
            "年": 31557600, "月": 2629800, "周": 604800, "天": 86400,
            "小时": 3600, "分钟": 60, "秒": 1,
            "毫秒": 0.001, "微秒": 1e-6, "纳秒": 1e-9
        }
    },
    "speed": {
        "name": "速度",
        "units": {
            "米/秒": 1, "公里/小时": 1/3.6,
            "英里/小时": 0.44704, "节": 0.514444
        }
    },
    "data": {
        "name": "数据存储",
        "units": {
            "PB": 1125899906842624, "TB": 1099511627776,
            "GB": 1073741824, "MB": 1048576, "KB": 1024,
            "字节": 1, "比特": 0.125
        }
    }
}

TEMPERATURE_UNITS = {
    "temperature": {
        "name": "温度",
        "units": ["摄氏度", "华氏度", "开尔文"]
    }
}

PRESETS = [
    {"name": "1英寸 = 2.54厘米", "category": "length", "from_unit": "英寸", "to_unit": "厘米", "value": 1},
    {"name": "1磅 = 0.4536千克", "category": "mass", "from_unit": "磅", "to_unit": "千克", "value": 1},
    {"name": "1加仑 = 3.785升", "category": "volume", "from_unit": "加仑(美)", "to_unit": "升", "value": 1},
    {"name": "1英里 = 1.609公里", "category": "length", "from_unit": "英里", "to_unit": "千米", "value": 1},
    {"name": "1海里 = 1.852公里", "category": "length", "from_unit": "海里", "to_unit": "千米", "value": 1},
    {"name": "1盎司 = 28.35克", "category": "mass", "from_unit": "盎司", "to_unit": "克", "value": 1},
]

HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')
EXCHANGE_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'exchange_cache.json')

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history[:10], f, ensure_ascii=False, indent=2)

def convert_temperature(value, from_unit, to_unit):
    if from_unit == to_unit:
        return value
    if from_unit == "摄氏度":
        if to_unit == "华氏度":
            return value * 9 / 5 + 32
        elif to_unit == "开尔文":
            return value + 273.15
    elif from_unit == "华氏度":
        if to_unit == "摄氏度":
            return (value - 32) * 5 / 9
        elif to_unit == "开尔文":
            return (value - 32) * 5 / 9 + 273.15
    elif from_unit == "开尔文":
        if to_unit == "摄氏度":
            return value - 273.15
        elif to_unit == "华氏度":
            return (value - 273.15) * 9 / 5 + 32
    return value

def convert_all(value, from_unit, category):
    if category == "temperature":
        results = {}
        for unit in TEMPERATURE_UNITS["temperature"]["units"]:
            if unit == from_unit:
                results[unit] = value
            else:
                results[unit] = convert_temperature(value, from_unit, unit)
        return results

    cat_data = UNITS[category]
    base_value = value * cat_data["units"][from_unit]
    results = {}
    for unit, factor in cat_data["units"].items():
        results[unit] = base_value / factor
    return results


@app.route('/api/categories')
def get_categories():
    result = []
    for key, val in UNITS.items():
        result.append({"key": key, "name": val["name"], "units": list(val["units"].keys())})
    for key, val in TEMPERATURE_UNITS.items():
        result.append({"key": key, "name": val["name"], "units": val["units"]})
    return jsonify(result)


@app.route('/api/convert', methods=['POST'])
def convert():
    data = request.json
    category = data.get('category')
    from_unit = data.get('from_unit')
    value = data.get('value', 0)
    precision = data.get('precision', 6)

    if category not in UNITS and category != "temperature":
        return jsonify({"error": "无效的单位类别"}), 400

    if category == "temperature" and from_unit not in TEMPERATURE_UNITS["temperature"]["units"]:
        return jsonify({"error": "无效的温度单位"}), 400

    if category != "temperature" and from_unit not in UNITS[category]["units"]:
        return jsonify({"error": "无效的单位"}), 400

    results = convert_all(value, from_unit, category)
    formatted = {}
    for unit, val in results.items():
        formatted[unit] = round(val, precision)

    history = load_history()
    history.insert(0, {
        "category": category,
        "from_unit": from_unit,
        "value": value,
        "precision": precision,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": formatted
    })
    history = history[:10]
    save_history(history)

    return jsonify({"results": formatted, "from_unit": from_unit, "value": value})


@app.route('/api/history')
def get_history():
    return jsonify(load_history())


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    save_history([])
    return jsonify({"message": "历史已清除"})


@app.route('/api/presets')
def get_presets():
    result = []
    for p in PRESETS:
        results = convert_all(p["value"], p["from_unit"], p["category"])
        result.append({**p, "result": results.get(p["to_unit"], 0)})
    return jsonify(result)


@app.route('/api/exchange')
def get_exchange_rates():
    cache = None
    if os.path.exists(EXCHANGE_CACHE_FILE):
        with open(EXCHANGE_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        cache_date = cache.get("date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if cache_date == today:
            return jsonify(cache)

    try:
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        data = resp.json()
        result = {
            "base": "USD",
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "rates": {}
        }
        for code in ["USD", "EUR", "CNY", "JPY", "GBP"]:
            result["rates"][code] = data.get("rates", {}).get(code, 1 if code == "USD" else 0)
        with open(EXCHANGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return jsonify(result)
    except Exception:
        if cache:
            return jsonify(cache)
        return jsonify({
            "base": "USD",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rates": {"USD": 1, "EUR": 0.92, "CNY": 7.24, "JPY": 149.5, "GBP": 0.79}
        })


@app.route('/api/exchange/convert', methods=['POST'])
def convert_currency():
    data = request.json
    from_currency = data.get('from_currency', 'USD')
    to_currency = data.get('to_currency', 'CNY')
    amount = data.get('amount', 1)

    try:
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        rates = resp.json().get("rates", {})
    except Exception:
        rates = {"USD": 1, "EUR": 0.92, "CNY": 7.24, "JPY": 149.5, "GBP": 0.79}

    from_rate = rates.get(from_currency, 1)
    to_rate = rates.get(to_currency, 1)
    if from_rate == 0:
        return jsonify({"error": "无效的源货币"}), 400
    result = amount / from_rate * to_rate
    return jsonify({"from": from_currency, "to": to_currency, "amount": amount, "result": round(result, 4)})


@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
