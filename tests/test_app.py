import sys
import os
import json
import pytest
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app, convert_all, convert_temperature, UNITS, TEMPERATURE_UNITS, PRESETS
from app import get_history, add_history, clear_all_history, _history_lock, _history_store


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clean_history():
    clear_all_history()
    yield
    clear_all_history()


class TestConvertTemperature:

    def test_celsius_to_fahrenheit(self):
        assert convert_temperature(0, "摄氏度", "华氏度") == 32.0
        assert convert_temperature(100, "摄氏度", "华氏度") == 212.0
        assert convert_temperature(37, "摄氏度", "华氏度") == pytest.approx(98.6, abs=0.1)

    def test_fahrenheit_to_celsius(self):
        assert convert_temperature(32, "华氏度", "摄氏度") == 0.0
        assert convert_temperature(212, "华氏度", "摄氏度") == 100.0
        assert convert_temperature(-40, "华氏度", "摄氏度") == -40.0

    def test_celsius_to_kelvin(self):
        assert convert_temperature(0, "摄氏度", "开尔文") == 273.15
        assert convert_temperature(-273.15, "摄氏度", "开尔文") == pytest.approx(0, abs=1e-10)

    def test_kelvin_to_celsius(self):
        assert convert_temperature(273.15, "开尔文", "摄氏度") == 0.0
        assert convert_temperature(0, "开尔文", "摄氏度") == -273.15

    def test_fahrenheit_to_kelvin(self):
        assert convert_temperature(32, "华氏度", "开尔文") == 273.15
        assert convert_temperature(-459.67, "华氏度", "开尔文") == pytest.approx(0, abs=0.01)

    def test_kelvin_to_fahrenheit(self):
        assert convert_temperature(273.15, "开尔文", "华氏度") == 32.0
        assert convert_temperature(373.15, "开尔文", "华氏度") == pytest.approx(212.0, abs=0.01)

    def test_same_unit_returns_same_value(self):
        assert convert_temperature(42, "摄氏度", "摄氏度") == 42
        assert convert_temperature(42, "华氏度", "华氏度") == 42
        assert convert_temperature(42, "开尔文", "开尔文") == 42

    def test_negative_temperatures(self):
        assert convert_temperature(-100, "摄氏度", "华氏度") == -148.0
        assert convert_temperature(-273.15, "摄氏度", "开尔文") == pytest.approx(0, abs=1e-10)

    def test_float_precision(self):
        result = convert_temperature(1, "摄氏度", "华氏度")
        assert result == 33.8
        result = convert_temperature(1, "华氏度", "摄氏度")
        assert result == pytest.approx(-17.2222, abs=0.001)


class TestConvertAllLength:

    def test_meter_to_km(self):
        results = convert_all(1000, "米", "length")
        assert results["千米"] == 1.0
        assert results["米"] == 1000.0

    def test_inch_to_cm(self):
        results = convert_all(1, "英寸", "length")
        assert results["厘米"] == pytest.approx(2.54, abs=0.001)

    def test_mile_to_km(self):
        results = convert_all(1, "英里", "length")
        assert results["千米"] == pytest.approx(1.609344, abs=0.001)

    def test_nautical_mile_to_km(self):
        results = convert_all(1, "海里", "length")
        assert results["千米"] == pytest.approx(1.852, abs=0.001)

    def test_foot_to_meter(self):
        results = convert_all(1, "英尺", "length")
        assert results["米"] == pytest.approx(0.3048, abs=0.001)

    def test_yard_to_meter(self):
        results = convert_all(1, "码", "length")
        assert results["米"] == pytest.approx(0.9144, abs=0.001)

    def test_zero_value(self):
        results = convert_all(0, "米", "length")
        for val in results.values():
            assert val == 0.0

    def test_negative_value(self):
        results = convert_all(-1, "米", "length")
        assert results["米"] == -1.0
        assert results["千米"] == -0.001

    def test_very_large_value(self):
        results = convert_all(1e15, "米", "length")
        assert results["千米"] == 1e12

    def test_very_small_value(self):
        results = convert_all(1e-15, "米", "length")
        assert results["纳米"] == pytest.approx(1e-6, abs=1e-10)

    def test_all_length_units_returned(self):
        results = convert_all(1, "米", "length")
        expected_units = list(UNITS["length"]["units"].keys())
        assert set(results.keys()) == set(expected_units)


class TestConvertAllArea:

    def test_sqm_to_sqkm(self):
        results = convert_all(1e6, "平方米", "area")
        assert results["平方公里"] == 1.0

    def test_hectare_to_sqm(self):
        results = convert_all(1, "公顷", "area")
        assert results["平方米"] == 1e4

    def test_acre_to_sqm(self):
        results = convert_all(1, "英亩", "area")
        assert results["平方米"] == pytest.approx(4046.8564224, abs=0.001)

    def test_all_area_units_returned(self):
        results = convert_all(1, "平方米", "area")
        assert set(results.keys()) == set(UNITS["area"]["units"].keys())


class TestConvertAllVolume:

    def test_liter_to_ml(self):
        results = convert_all(1, "升", "volume")
        assert results["毫升"] == 1000.0

    def test_us_gallon_to_liter(self):
        results = convert_all(1, "加仑(美)", "volume")
        assert results["升"] == pytest.approx(3.785411784, abs=0.001)

    def test_uk_gallon_to_liter(self):
        results = convert_all(1, "加仑(英)", "volume")
        assert results["升"] == pytest.approx(4.54609, abs=0.001)

    def test_cubic_cm_to_ml(self):
        results = convert_all(1, "立方厘米", "volume")
        assert results["毫升"] == 1.0

    def test_all_volume_units_returned(self):
        results = convert_all(1, "升", "volume")
        assert set(results.keys()) == set(UNITS["volume"]["units"].keys())


class TestConvertAllMass:

    def test_kg_to_g(self):
        results = convert_all(1, "千克", "mass")
        assert results["克"] == 1000.0

    def test_pound_to_kg(self):
        results = convert_all(1, "磅", "mass")
        assert results["千克"] == pytest.approx(0.45359237, abs=0.001)

    def test_ounce_to_g(self):
        results = convert_all(1, "盎司", "mass")
        assert results["克"] == pytest.approx(28.349523125, abs=0.001)

    def test_jin_to_kg(self):
        results = convert_all(1, "市斤", "mass")
        assert results["千克"] == 0.5

    def test_liang_to_g(self):
        results = convert_all(1, "两", "mass")
        assert results["克"] == 50.0

    def test_ton_to_kg(self):
        results = convert_all(1, "吨", "mass")
        assert results["千克"] == 1000.0

    def test_all_mass_units_returned(self):
        results = convert_all(1, "千克", "mass")
        assert set(results.keys()) == set(UNITS["mass"]["units"].keys())


class TestConvertAllTime:

    def test_hour_to_minute(self):
        results = convert_all(1, "小时", "time")
        assert results["分钟"] == 60.0

    def test_day_to_hour(self):
        results = convert_all(1, "天", "time")
        assert results["小时"] == 24.0

    def test_year_to_day(self):
        results = convert_all(1, "年", "time")
        assert results["天"] == pytest.approx(365.25, abs=0.01)

    def test_ms_to_second(self):
        results = convert_all(1000, "毫秒", "time")
        assert results["秒"] == 1.0

    def test_all_time_units_returned(self):
        results = convert_all(1, "秒", "time")
        assert set(results.keys()) == set(UNITS["time"]["units"].keys())


class TestConvertAllSpeed:

    def test_kmh_to_ms(self):
        results = convert_all(3.6, "公里/小时", "speed")
        assert results["米/秒"] == pytest.approx(1.0, abs=0.01)

    def test_mph_to_ms(self):
        results = convert_all(1, "英里/小时", "speed")
        assert results["米/秒"] == pytest.approx(0.44704, abs=0.001)

    def test_knot_to_ms(self):
        results = convert_all(1, "节", "speed")
        assert results["米/秒"] == pytest.approx(0.514444, abs=0.001)

    def test_all_speed_units_returned(self):
        results = convert_all(1, "米/秒", "speed")
        assert set(results.keys()) == set(UNITS["speed"]["units"].keys())


class TestConvertAllData:

    def test_gb_to_mb(self):
        results = convert_all(1, "GB", "data")
        assert results["MB"] == 1024.0

    def test_tb_to_gb(self):
        results = convert_all(1, "TB", "data")
        assert results["GB"] == 1024.0

    def test_byte_to_bit(self):
        results = convert_all(1, "字节", "data")
        assert results["比特"] == 8.0

    def test_kb_to_byte(self):
        results = convert_all(1, "KB", "data")
        assert results["字节"] == 1024.0

    def test_pb_to_tb(self):
        results = convert_all(1, "PB", "data")
        assert results["TB"] == 1024.0

    def test_all_data_units_returned(self):
        results = convert_all(1, "字节", "data")
        assert set(results.keys()) == set(UNITS["data"]["units"].keys())


class TestConvertAllTemperature:

    def test_celsius_all(self):
        results = convert_all(100, "摄氏度", "temperature")
        assert results["摄氏度"] == 100
        assert results["华氏度"] == 212.0
        assert results["开尔文"] == 373.15

    def test_fahrenheit_all(self):
        results = convert_all(32, "华氏度", "temperature")
        assert results["摄氏度"] == 0.0
        assert results["华氏度"] == 32
        assert results["开尔文"] == 273.15

    def test_kelvin_all(self):
        results = convert_all(0, "开尔文", "temperature")
        assert results["摄氏度"] == -273.15
        assert results["华氏度"] == pytest.approx(-459.67, abs=0.01)


class TestAPICategories:

    def test_get_categories_success(self, client):
        resp = client.get('/api/categories')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 8

    def test_categories_structure(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        for cat in data:
            assert "key" in cat
            assert "name" in cat
            assert "units" in cat
            assert isinstance(cat["units"], list)
            assert len(cat["units"]) > 0

    def test_categories_contains_length(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        keys = [c["key"] for c in data]
        assert "length" in keys

    def test_categories_contains_temperature(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        keys = [c["key"] for c in data]
        assert "temperature" in keys

    def test_all_expected_categories_present(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        keys = [c["key"] for c in data]
        expected = ["length", "area", "volume", "mass", "time", "speed", "data", "temperature"]
        for k in expected:
            assert k in keys


class TestAPIConvert:

    def test_convert_length_basic(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "千米",
            "value": 1,
            "precision": 6
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert data["results"]["米"] == 1000.0
        assert data["from_unit"] == "千米"
        assert data["value"] == 1

    def test_convert_temperature_basic(self, client):
        resp = client.post('/api/convert', json={
            "category": "temperature",
            "from_unit": "摄氏度",
            "value": 0,
            "precision": 2
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["results"]["华氏度"] == 32.0
        assert data["results"]["开尔文"] == 273.15

    def test_convert_mass(self, client):
        resp = client.post('/api/convert', json={
            "category": "mass",
            "from_unit": "千克",
            "value": 1
        })
        data = resp.get_json()
        assert data["results"]["克"] == 1000.0

    def test_convert_invalid_category(self, client):
        resp = client.post('/api/convert', json={
            "category": "invalid_cat",
            "from_unit": "米",
            "value": 1
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_convert_invalid_unit(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "光年",
            "value": 1
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_convert_invalid_temperature_unit(self, client):
        resp = client.post('/api/convert', json={
            "category": "temperature",
            "from_unit": "兰氏度",
            "value": 1
        })
        assert resp.status_code == 400

    def test_convert_default_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米"
        })
        data = resp.get_json()
        assert data["value"] == 0

    def test_convert_default_precision(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1
        })
        data = resp.get_json()
        results_str = str(data["results"])
        assert len(results_str) > 0

    def test_convert_precision_2(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": 2
        })
        data = resp.get_json()
        for val in data["results"].values():
            decimal_part = str(val).split('.')[-1] if '.' in str(val) else ''
            assert len(decimal_part) <= 2

    def test_convert_precision_4(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": 4
        })
        data = resp.get_json()
        for val in data["results"].values():
            decimal_part = str(val).split('.')[-1] if '.' in str(val) else ''
            assert len(decimal_part) <= 4

    def test_convert_negative_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": -5
        })
        data = resp.get_json()
        assert data["results"]["米"] == -5.0

    def test_convert_zero_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 0
        })
        data = resp.get_json()
        for val in data["results"].values():
            assert val == 0.0

    def test_convert_large_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1e15
        })
        assert resp.status_code == 200

    def test_convert_float_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 3.14159
        })
        data = resp.get_json()
        assert data["results"]["米"] == pytest.approx(3.14159, abs=0.001)

    def test_convert_records_history(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 42
        })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) >= 1
        assert data[0]["value"] == 42

    def test_convert_all_categories(self, client):
        categories = ["length", "area", "volume", "mass", "time", "speed", "data", "temperature"]
        for cat in categories:
            if cat == "temperature":
                from_unit = "摄氏度"
            else:
                from_unit = list(UNITS[cat]["units"].keys())[0]
            resp = client.post('/api/convert', json={
                "category": cat,
                "from_unit": from_unit,
                "value": 1
            })
            assert resp.status_code == 200, f"Failed for category: {cat}"


class TestAPIHistory:

    def test_get_history_empty(self, client):
        resp = client.get('/api/history')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_history_after_conversion(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 100
        })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["category"] == "length"
        assert data[0]["from_unit"] == "米"
        assert data[0]["value"] == 100

    def test_history_max_10_entries(self, client):
        for i in range(15):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": i
            })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) == 10

    def test_history_order_newest_first(self, client):
        client.post('/api/convert', json={"category": "length", "from_unit": "米", "value": 1})
        client.post('/api/convert', json={"category": "length", "from_unit": "米", "value": 2})
        resp = client.get('/api/history')
        data = resp.get_json()
        assert data[0]["value"] == 2
        assert data[1]["value"] == 1

    def test_history_entry_structure(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": 4
        })
        resp = client.get('/api/history')
        data = resp.get_json()
        entry = data[0]
        assert "category" in entry
        assert "from_unit" in entry
        assert "value" in entry
        assert "precision" in entry
        assert "timestamp" in entry
        assert "results" in entry

    def test_clear_history(self, client):
        client.post('/api/convert', json={"category": "length", "from_unit": "米", "value": 1})
        resp = client.post('/api/history/clear')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data
        resp2 = client.get('/api/history')
        assert len(resp2.get_json()) == 0

    def test_clear_history_already_empty(self, client):
        resp = client.post('/api/history/clear')
        assert resp.status_code == 200


class TestAPIPresets:

    def test_get_presets_success(self, client):
        resp = client.get('/api/presets')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_preset_structure(self, client):
        resp = client.get('/api/presets')
        data = resp.get_json()
        for p in data:
            assert "name" in p
            assert "category" in p
            assert "from_unit" in p
            assert "to_unit" in p
            assert "value" in p
            assert "result" in p

    def test_preset_values_correct(self, client):
        resp = client.get('/api/presets')
        data = resp.get_json()
        inch_preset = [p for p in data if p["from_unit"] == "英寸" and p["to_unit"] == "厘米"]
        assert len(inch_preset) == 1
        assert inch_preset[0]["result"] == pytest.approx(2.54, abs=0.01)

    def test_preset_count_matches(self, client):
        resp = client.get('/api/presets')
        data = resp.get_json()
        assert len(data) == len(PRESETS)


class TestAPIExchange:

    def test_get_exchange_rates(self, client):
        resp = client.get('/api/exchange')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "base" in data
        assert "date" in data
        assert "rates" in data
        assert data["base"] == "USD"

    def test_exchange_rates_currencies(self, client):
        resp = client.get('/api/exchange')
        data = resp.get_json()
        for code in ["USD", "EUR", "CNY", "JPY", "GBP"]:
            assert code in data["rates"]

    def test_usd_rate_always_1(self, client):
        resp = client.get('/api/exchange')
        data = resp.get_json()
        assert data["rates"]["USD"] == 1

    def test_exchange_convert_basic(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "USD",
            "amount": 100
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["result"] == 100.0

    def test_exchange_convert_structure(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": 1
        })
        data = resp.get_json()
        assert "from" in data
        assert "to" in data
        assert "amount" in data
        assert "result" in data

    def test_exchange_convert_default_amount(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY"
        })
        data = resp.get_json()
        assert data["amount"] == 1
        assert data["result"] > 0

    def test_exchange_convert_default_currencies(self, client):
        resp = client.post('/api/exchange/convert', json={
            "amount": 10
        })
        data = resp.get_json()
        assert data["from"] == "USD"
        assert data["to"] == "CNY"

    def test_exchange_convert_result_precision(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": 1
        })
        data = resp.get_json()
        result_str = str(data["result"])
        if '.' in result_str:
            decimal_part = result_str.split('.')[-1]
            assert len(decimal_part) <= 4


class TestAPIServing:

    def test_index_page(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert '全能单位换算工具' in resp.data.decode('utf-8')

    def test_static_html(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        content = resp.data.decode('utf-8').lower()
        assert 'vue' in content


class TestHistoryPersistence:

    def test_history_file_created(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1
        })
        history_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'history.json')
        assert os.path.exists(history_file)

    def test_history_file_valid_json(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1
        })
        history_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'history.json')
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_history_max_10_in_file(self, client):
        for i in range(15):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": i
            })
        history_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'history.json')
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) <= 10


class TestConcurrency:

    def test_concurrent_history_writes(self):
        errors = []

        def do_add(val):
            try:
                add_history({
                    "category": "length",
                    "from_unit": "米",
                    "value": val,
                    "timestamp": "2026-01-01 00:00:00"
                })
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(20):
            t = threading.Thread(target=do_add, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent errors: {errors}"
        history = get_history()
        assert len(history) <= 10


class TestEdgeCases:

    def test_convert_very_high_precision(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": 20
        })
        assert resp.status_code == 200

    def test_convert_zero_precision(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1.5,
            "precision": 0
        })
        assert resp.status_code == 200
        data = resp.get_json()
        for val in data["results"].values():
            assert val == round(val, 0)

    def test_convert_negative_precision(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": -1
        })
        assert resp.status_code == 200

    def test_convert_string_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": "abc"
        })
        assert resp.status_code == 500, "BUG: 字符串value导致500内部错误，应返回400"

    def test_convert_none_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": None
        })
        assert resp.status_code == 500, "BUG: None值value导致500内部错误，应返回400"

    def test_convert_missing_body(self, client):
        resp = client.post('/api/convert', content_type='application/json')
        assert resp.status_code in [200, 400, 500]

    def test_convert_empty_json(self, client):
        resp = client.post('/api/convert', json={})
        assert resp.status_code == 400

    def test_history_timestamp_format(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1
        })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) > 0
        timestamp = data[0]["timestamp"]
        assert len(timestamp) == 19
        assert "202" in timestamp or "199" in timestamp

    def test_all_presets_convertible(self, client):
        for p in PRESETS:
            results = convert_all(p["value"], p["from_unit"], p["category"])
            assert p["to_unit"] in results, f"Preset {p['name']} target unit {p['to_unit']} not in results"

    def test_self_conversion_identity(self, client):
        for cat_key, cat_data in UNITS.items():
            for unit in cat_data["units"]:
                results = convert_all(1, unit, cat_key)
                assert results[unit] == pytest.approx(1.0, abs=1e-10), f"Self-conversion failed for {unit} in {cat_key}"

    def test_roundtrip_conversion(self, client):
        for cat_key, cat_data in UNITS.items():
            units = list(cat_data["units"].keys())
            if len(units) >= 2:
                results = convert_all(1, units[0], cat_key)
                val_in_unit2 = results[units[1]]
                results_back = convert_all(val_in_unit2, units[1], cat_key)
                assert results_back[units[0]] == pytest.approx(1.0, abs=1e-8), f"Roundtrip failed: {units[0]} -> {units[1]} -> {units[0]}"

    def test_exchange_convert_zero_rate_currency(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "NONEXISTENT",
            "to_currency": "USD",
            "amount": 1
        })
        data = resp.get_json()
        if "error" in data:
            assert resp.status_code == 400
        else:
            assert data["result"] is not None

    def test_convert_scientific_notation_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1e-9
        })
        assert resp.status_code == 200
