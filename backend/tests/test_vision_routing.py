from types import SimpleNamespace
from unittest.mock import patch

import pytest
from starlette.requests import Request
from backend.app.services.vision import detect_image, mobile_request
from backend.tests.test_p0_flow import env, account, png


@pytest.mark.parametrize('headers, expected', [
    ({}, False),
    ({'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, False),
    ({'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)'}, True),
    ({'user-agent': 'Mozilla/5.0 (Linux; Android 14)'}, True),
    ({'user-agent': 'Mozilla/5.0 (iPad; CPU OS 18_0)'}, True),
    ({'sec-ch-ua-mobile': '?1'}, True),
    ({'sec-ch-ua-mobile': '?0', 'user-agent': 'Android'}, True),
])
def test_device_selection(headers, expected):
    request = Request({'type': 'http', 'headers': [
        (key.encode(), value.encode()) for key, value in headers.items()]})
    assert mobile_request(request) is expected


@pytest.mark.parametrize('mobile, profile', [(False, 'web'), (True, 'mobile')])
def test_worker_receives_device_profile(mobile, profile):
    with patch('backend.app.services.vision.subprocess.run', return_value=SimpleNamespace(
            returncode=0, stdout='{"detections": [], "model_version": "test"}')) as run:
        assert detect_image('photo.jpg', mobile=mobile)['detections'] == []
    assert run.call_args.args[0][-2:] == ['photo.jpg', profile]


@pytest.mark.parametrize('agent, expected', [('iPhone', True), ('Windows NT', False)])
def test_photo_endpoint_routes_model(env, agent, expected):
    client, _, monkeypatch = env
    account(client)
    calls = []

    def infer(path, *, mobile=False):
        calls.append(mobile)
        return {'detections': [], 'model_version': 'test'}

    monkeypatch.setattr('backend.app.api.detect_image', infer)
    response = client.post('/meals/detect', headers={'user-agent': agent},
                           files={'file': ('test.png', png(), 'image/png')})
    assert response.status_code == 200
    assert calls == [expected]
