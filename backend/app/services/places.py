# 칼로티 코치 음식점 검색(카카오 로컬 키워드 검색). 업무지시서 v1.2 restaurant_search.
# 음식점은 지도 API가 돌려준 곳만 보여 준다. 위치는 사용자가 말한 지역명 또는 브라우저가 보낸 좌표만 쓰고 저장하지 않는다.
import logging
import httpx
from ..config import settings

logger = logging.getLogger('calodetect')
SEARCH_URL = 'https://dapi.kakao.com/v2/local/search/keyword.json'


class PlacesUnavailable(Exception):
    pass


def api_key():
    return settings.kakao_rest_api_key or settings.kakao_client_id


def available():
    return bool(api_key())


# query: 음식 종류(예: 샐러드), area: 지역명(예: 강남역), lat/lng: 현재 위치. 가까운 순 최대 size곳.
def search(query, area=None, lat=None, lng=None, size=5):
    if not api_key():
        raise PlacesUnavailable('missing key')
    keyword = ' '.join(part for part in (area, query or '맛집') if part)
    params = {'query': keyword[:100], 'category_group_code': 'FD6', 'size': size}
    if lat is not None and lng is not None:
        params.update({'x': f'{lng:.6f}', 'y': f'{lat:.6f}', 'radius': 2000, 'sort': 'distance'})
    try:
        response = httpx.get(SEARCH_URL, params=params, headers={'Authorization': f'KakaoAK {api_key()}'}, timeout=10)
        response.raise_for_status()
        documents = response.json().get('documents') or []
    except Exception as error:
        logger.warning('kakao place search failed: %s', type(error).__name__)
        raise PlacesUnavailable(type(error).__name__) from error
    return [{'name': d.get('place_name', ''), 'category': (d.get('category_name') or '').split(' > ')[-1],
             'address': d.get('road_address_name') or d.get('address_name') or '',
             'distance': int(d['distance']) if str(d.get('distance') or '').isdigit() else None,
             'phone': d.get('phone') or '', 'url': d.get('place_url') or ''} for d in documents]
