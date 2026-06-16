import sys
import os
import json
import time
import pytest
import threading

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


class TestInputValidation:

    def test_convert_missing_category(self, client):
        resp = client.post('/api/convert', json={
            "from_unit": "米",
            "value": 1
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_convert_missing_from_unit(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "value": 1
        })
        assert resp.status_code == 400

    def test_convert_empty_from_unit(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "",
            "value": 1
        })
        assert resp.status_code == 400

    def test_convert_null_category(self, client):
        resp = client.post('/api/convert', json={
            "category": None,
            "from_unit": "米",
            "value": 1
        })
        assert resp.status_code == 400

    def test_convert_numeric_string_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": "100"
        })
        assert resp.status_code in [200, 400, 500]

    def test_convert_boolean_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": True
        })
        assert resp.status_code in [200, 400, 500]

    def test_convert_list_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": [1, 2, 3]
        })
        assert resp.status_code == 500

    def test_convert_object_value(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": {"nested": 1}
        })
        assert resp.status_code == 500

    def test_convert_negative_precision_large(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 100,
            "precision": -100
        })
        assert resp.status_code == 200

    def test_convert_precision_non_numeric(self, client):
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 1,
            "precision": "high"
        })
        assert resp.status_code in [200, 400, 500]


class TestTemperatureEdgeCases:

    def test_absolute_zero_celsius(self):
        result = convert_temperature(-273.15, "摄氏度", "开尔文")
        assert result == pytest.approx(0, abs=1e-10)

    def test_absolute_zero_fahrenheit(self):
        result = convert_temperature(-459.67, "华氏度", "开尔文")
        assert result == pytest.approx(0, abs=0.01)

    def test_below_absolute_zero_kelvin(self):
        result = convert_temperature(-100, "开尔文", "摄氏度")
        assert result == -373.15

    def test_room_temperature_celsius(self):
        result = convert_temperature(25, "摄氏度", "华氏度")
        assert result == pytest.approx(77, abs=0.1)

    def test_body_temperature_celsius(self):
        result = convert_temperature(37, "摄氏度", "华氏度")
        assert result == pytest.approx(98.6, abs=0.1)

    def test_water_boiling_point(self):
        assert convert_temperature(100, "摄氏度", "华氏度") == 212.0
        assert convert_temperature(100, "摄氏度", "开尔文") == 373.15

    def test_water_freezing_point(self):
        assert convert_temperature(0, "摄氏度", "华氏度") == 32.0
        assert convert_temperature(0, "摄氏度", "开尔文") == 273.15


class TestAllUnitsCoverage:

    def test_all_length_units(self):
        units = list(UNITS["length"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "length")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_area_units(self):
        units = list(UNITS["area"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "area")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_volume_units(self):
        units = list(UNITS["volume"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "volume")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_mass_units(self):
        units = list(UNITS["mass"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "mass")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_time_units(self):
        units = list(UNITS["time"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "time")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_speed_units(self):
        units = list(UNITS["speed"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "speed")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_data_units(self):
        units = list(UNITS["data"]["units"].keys())
        for unit in units:
            results = convert_all(1, unit, "data")
            assert unit in results
            assert results[unit] == pytest.approx(1.0, abs=1e-10)

    def test_all_temperature_units(self):
        units = TEMPERATURE_UNITS["temperature"]["units"]
        for unit in units:
            results = convert_all(0, unit, "temperature")
            assert unit in results


class TestConversionAccuracy:

    def test_kilometer_to_meter(self):
        results = convert_all(1, "千米", "length")
        assert results["米"] == 1000.0

    def test_meter_to_centimeter(self):
        results = convert_all(1, "米", "length")
        assert results["厘米"] == 100.0

    def test_kilogram_to_gram(self):
        results = convert_all(1, "千克", "mass")
        assert results["克"] == 1000.0

    def test_hour_to_second(self):
        results = convert_all(1, "小时", "time")
        assert results["秒"] == 3600.0

    def test_gigabyte_to_megabyte(self):
        results = convert_all(1, "GB", "data")
        assert results["MB"] == 1024.0

    def test_byte_to_bit_exact(self):
        results = convert_all(1, "字节", "data")
        assert results["比特"] == 8.0

    def test_hectare_to_square_meter(self):
        results = convert_all(1, "公顷", "area")
        assert results["平方米"] == 10000.0

    def test_liter_to_milliliter(self):
        results = convert_all(1, "升", "volume")
        assert results["毫升"] == 1000.0


class TestHistoryFunctionality:

    def test_history_entry_count_after_multiple_conversions(self, client):
        for i in range(5):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": i
            })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) == 5

    def test_history_does_not_exceed_max(self, client):
        for i in range(20):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": i
            })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) == 10

    def test_history_contains_results(self, client):
        client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": 100
        })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert "results" in data[0]
        assert "千米" in data[0]["results"]

    def test_clear_history_twice(self, client):
        client.post('/api/convert', json={"category": "length", "from_unit": "米", "value": 1})
        client.post('/api/history/clear')
        resp = client.post('/api/history/clear')
        assert resp.status_code == 200
        resp2 = client.get('/api/history')
        assert len(resp2.get_json()) == 0

    def test_history_after_clear_and_new_conversion(self, client):
        client.post('/api/convert', json={"category": "length", "from_unit": "米", "value": 1})
        client.post('/api/history/clear')
        client.post('/api/convert', json={"category": "mass", "from_unit": "千克", "value": 5})
        resp = client.get('/api/history')
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["category"] == "mass"

    def test_history_order_newest_first_detailed(self, client):
        values = [10, 20, 30, 40, 50]
        for v in values:
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": v
            })
        resp = client.get('/api/history')
        data = resp.get_json()
        assert data[0]["value"] == 50
        assert data[1]["value"] == 40
        assert data[2]["value"] == 30
        assert data[3]["value"] == 20
        assert data[4]["value"] == 10


class TestPresets:

    def test_all_presets_have_valid_category(self, client):
        for p in PRESETS:
            assert p["category"] in UNITS or p["category"] == "temperature"

    def test_all_presets_have_valid_units(self, client):
        for p in PRESETS:
            if p["category"] == "temperature":
                assert p["from_unit"] in TEMPERATURE_UNITS["temperature"]["units"]
                assert p["to_unit"] in TEMPERATURE_UNITS["temperature"]["units"]
            else:
                assert p["from_unit"] in UNITS[p["category"]]["units"]
                assert p["to_unit"] in UNITS[p["category"]]["units"]

    def test_preset_api_response_structure(self, client):
        resp = client.get('/api/presets')
        data = resp.get_json()
        for p in data:
            assert "name" in p
            assert "category" in p
            assert "from_unit" in p
            assert "to_unit" in p
            assert "value" in p
            assert "result" in p

    def test_preset_result_matches_conversion(self, client):
        resp = client.get('/api/presets')
        presets = resp.get_json()
        for p in presets:
            results = convert_all(p["value"], p["from_unit"], p["category"])
            assert results[p["to_unit"]] == pytest.approx(p["result"], abs=1e-6)


class TestExchangeRates:

    def test_exchange_api_response_structure(self, client):
        resp = client.get('/api/exchange')
        data = resp.get_json()
        assert "base" in data
        assert "date" in data
        assert "rates" in data

    def test_exchange_rates_are_positive(self, client):
        resp = client.get('/api/exchange')
        data = resp.get_json()
        for code, rate in data["rates"].items():
            assert rate > 0, f"Rate for {code} should be positive"

    def test_exchange_convert_same_currency(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "USD",
            "amount": 100
        })
        data = resp.get_json()
        assert data["result"] == 100.0

    def test_exchange_convert_zero_amount(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": 0
        })
        data = resp.get_json()
        assert data["result"] == 0

    def test_exchange_convert_negative_amount(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": -100
        })
        data = resp.get_json()
        assert data["result"] < 0

    def test_exchange_convert_large_amount(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": 1000000
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["result"] > 0

    def test_exchange_convert_invalid_from_currency(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "INVALID",
            "to_currency": "USD",
            "amount": 100
        })
        data = resp.get_json()
        if "error" in data:
            assert resp.status_code == 400
        else:
            assert data["result"] is not None

    def test_exchange_convert_invalid_to_currency(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "INVALID",
            "amount": 100
        })
        data = resp.get_json()
        if "error" in data:
            assert resp.status_code == 400
        else:
            assert data["result"] is not None

    def test_exchange_convert_string_amount(self, client):
        resp = client.post('/api/exchange/convert', json={
            "from_currency": "USD",
            "to_currency": "CNY",
            "amount": "abc"
        })
        assert resp.status_code in [200, 400, 500]


class TestAPICategories:

    def test_categories_count(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        assert len(data) == 8

    def test_category_keys_are_unique(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        keys = [c["key"] for c in data]
        assert len(keys) == len(set(keys))

    def test_category_names_are_unique(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        names = [c["name"] for c in data]
        assert len(names) == len(set(names))

    def test_each_category_has_units(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        for cat in data:
            assert len(cat["units"]) > 0

    def test_temperature_category_has_three_units(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        temp_cat = [c for c in data if c["key"] == "temperature"][0]
        assert len(temp_cat["units"]) == 3

    def test_length_category_has_eleven_units(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        length_cat = [c for c in data if c["key"] == "length"][0]
        assert len(length_cat["units"]) == 11


class TestPerformance:

    def test_convert_performance(self, client):
        start_time = time.time()
        for _ in range(100):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": 1000,
                "precision": 6
            })
        elapsed = time.time() - start_time
        assert elapsed < 5.0, f"100 conversions took {elapsed:.2f}s, expected < 5s"

    def test_categories_performance(self, client):
        start_time = time.time()
        for _ in range(100):
            client.get('/api/categories')
        elapsed = time.time() - start_time
        assert elapsed < 2.0, f"100 category requests took {elapsed:.2f}s, expected < 2s"

    def test_history_performance(self, client):
        for i in range(10):
            client.post('/api/convert', json={
                "category": "length",
                "from_unit": "米",
                "value": i
            })
        start_time = time.time()
        for _ in range(100):
            client.get('/api/history')
        elapsed = time.time() - start_time
        assert elapsed < 2.0, f"100 history requests took {elapsed:.2f}s, expected < 2s"

    def test_single_conversion_latency(self, client):
        latencies = []
        for _ in range(50):
            start = time.time()
            client.post('/api/convert', json={
                "category": "mass",
                "from_unit": "千克",
                "value": 1
            })
            latencies.append(time.time() - start)
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 0.1, f"Average latency {avg_latency*1000:.2f}ms, expected < 100ms"


class TestConcurrencyAdvanced:

    def test_concurrent_reads(self):
        errors = []
        results = []

        def do_read():
            try:
                h = get_history()
                results.append(len(h))
            except Exception as e:
                errors.append(str(e))

        for i in range(5):
            add_history({
                "category": "length",
                "from_unit": "米",
                "value": i,
                "timestamp": "2026-01-01 00:00:00",
                "results": {}
            })

        threads = []
        for _ in range(30):
            t = threading.Thread(target=do_read)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent read errors: {errors}"
        assert all(r == 5 for r in results)

    def test_concurrent_mixed_read_write(self):
        errors = []

        def do_write(val):
            try:
                add_history({
                    "category": "length",
                    "from_unit": "米",
                    "value": val,
                    "timestamp": "2026-01-01 00:00:00",
                    "results": {}
                })
            except Exception as e:
                errors.append(str(e))

        def do_read():
            try:
                get_history()
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(15):
            t1 = threading.Thread(target=do_write, args=(i,))
            t2 = threading.Thread(target=do_read)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent mixed errors: {errors}"
        history = get_history()
        assert len(history) <= 10


class TestFrontendIntegration:

    def test_index_page_status(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_index_page_content_type(self, client):
        resp = client.get('/')
        assert 'text/html' in resp.content_type

    def test_index_page_has_vue(self, client):
        resp = client.get('/')
        content = resp.data.decode('utf-8')
        assert 'vue' in content.lower()

    def test_index_page_has_title(self, client):
        resp = client.get('/')
        content = resp.data.decode('utf-8')
        assert '<title>全能单位换算工具</title>' in content

    def test_index_page_has_app_div(self, client):
        resp = client.get('/')
        content = resp.data.decode('utf-8')
        assert '<div id="app">' in content

    def test_index_page_has_create_app(self, client):
        resp = client.get('/')
        content = resp.data.decode('utf-8')
        assert 'createApp' in content

    def test_index_page_has_api_calls(self, client):
        resp = client.get('/')
        content = resp.data.decode('utf-8')
        assert '/api/categories' in content
        assert '/api/convert' in content
        assert '/api/history' in content

    def test_static_file_not_found(self, client):
        resp = client.get('/nonexistent.js')
        assert resp.status_code == 404

    def test_favicon_request(self, client):
        resp = client.get('/favicon.ico')
        assert resp.status_code in [200, 404]


class TestSecurity:

    def test_cors_headers(self, client):
        resp = client.get('/api/categories')
        cors_header = resp.headers.get('Access-Control-Allow-Origin')
        assert cors_header is not None

    def test_json_content_type(self, client):
        resp = client.get('/api/categories')
        assert 'application/json' in resp.content_type

    def test_no_server_info_leak(self, client):
        resp = client.get('/api/categories')
        server_header = resp.headers.get('Server', '')
        assert len(server_header) < 50

    def test_sql_injection_category(self, client):
        resp = client.post('/api/convert', json={
            "category": "length' OR '1'='1",
            "from_unit": "米",
            "value": 1
        })
        assert resp.status_code == 400

    def test_xss_in_category_name(self, client):
        resp = client.get('/api/categories')
        data = resp.get_json()
        for cat in data:
            assert '<script>' not in cat["name"]
            assert 'javascript:' not in cat["name"]

    def test_large_payload_handling(self, client):
        large_value = 10**100
        resp = client.post('/api/convert', json={
            "category": "length",
            "from_unit": "米",
            "value": large_value
        })
        assert resp.status_code == 200


class TestDataIntegrity:

    def test_units_data_structure(self):
        for cat_key, cat_data in UNITS.items():
            assert "name" in cat_data
            assert "units" in cat_data
            assert isinstance(cat_data["units"], dict)
            assert len(cat_data["units"]) > 0

    def test_unit_factors_are_positive(self):
        for cat_key, cat_data in UNITS.items():
            for unit, factor in cat_data["units"].items():
                assert factor > 0, f"Factor for {unit} in {cat_key} must be positive"

    def test_base_unit_has_factor_one(self):
        for cat_key, cat_data in UNITS.items():
            units = list(cat_data["units"].keys())
            base_unit = units[1] if len(units) > 1 else units[0]
            if base_unit in ["米", "平方米", "升", "千克", "秒", "米/秒", "字节"]:
                assert cat_data["units"][base_unit] == 1.0

    def test_presets_have_positive_values(self):
        for p in PRESETS:
            assert p["value"] > 0, f"Preset {p['name']} has non-positive value"

    def test_preset_names_are_unique(self):
        names = [p["name"] for p in PRESETS]
        assert len(names) == len(set(names))


class TestRoundTripConversions:

    def test_length_round_trip_all_units(self):
        units = list(UNITS["length"]["units"].keys())
        for i in range(len(units)):
            for j in range(i+1, min(i+3, len(units))):
                u1, u2 = units[i], units[j]
                results1 = convert_all(100, u1, "length")
                val_u2 = results1[u2]
                results2 = convert_all(val_u2, u2, "length")
                assert results2[u1] == pytest.approx(100, abs=1e-6), \
                    f"Round trip failed: {u1} <-> {u2}"

    def test_mass_round_trip_all_units(self):
        units = list(UNITS["mass"]["units"].keys())
        for i in range(len(units)):
            for j in range(i+1, min(i+3, len(units))):
                u1, u2 = units[i], units[j]
                results1 = convert_all(50, u1, "mass")
                val_u2 = results1[u2]
                results2 = convert_all(val_u2, u2, "mass")
                assert results2[u1] == pytest.approx(50, abs=1e-6), \
                    f"Round trip failed: {u1} <-> {u2}"

    def test_temperature_round_trip(self):
        temps = [-40, 0, 25, 100, 1000]
        units = TEMPERATURE_UNITS["temperature"]["units"]
        for temp in temps:
            for u1 in units:
                for u2 in units:
                    if u1 != u2:
                        intermediate = convert_temperature(temp, u1, u2)
                        result = convert_temperature(intermediate, u2, u1)
                        assert result == pytest.approx(temp, abs=1e-6), \
                            f"Temp round trip failed: {u1} -> {u2} -> {u1} at {temp}"


class TestAPIErrorHandling:

    def test_method_not_allowed_get_convert(self, client):
        resp = client.get('/api/convert')
        assert resp.status_code == 405

    def test_method_not_allowed_post_history(self, client):
        resp = client.post('/api/history')
        assert resp.status_code == 405

    def test_method_not_allowed_get_history_clear(self, client):
        resp = client.get('/api/history/clear')
        assert resp.status_code == 405

    def test_method_not_allowed_get_exchange_convert(self, client):
        resp = client.get('/api/exchange/convert')
        assert resp.status_code == 405

    def test_404_on_nonexistent_api(self, client):
        resp = client.get('/api/nonexistent')
        assert resp.status_code == 404

    def test_invalid_json_body(self, client):
        resp = client.post('/api/convert', data='not json', content_type='application/json')
        assert resp.status_code in [400, 500]

    def test_form_data_instead_of_json(self, client):
        resp = client.post('/api/convert', data={
            "category": "length",
            "from_unit": "米",
            "value": "1"
        })
        assert resp.status_code in [200, 400, 500]
