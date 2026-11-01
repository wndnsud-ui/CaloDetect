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


# 업종 이름이 너무 넓어 메뉴 일치 판단에 쓰지 않는 카카오 분류.
GENERIC_CATEGORIES = {'음식점', '한식', '양식', '중식', '일식', '분식', '아시아음식', '술집', '간식', '카페', '퓨전요리', '뷔페'}


# 카카오 로컬은 메뉴판을 주지 않는다. 가게 이름이나 업종에 메뉴 이름이 있으면(예: 샐러드 → 샐러드 업종,
# 후라이드치킨 → 치킨 업종) 그 메뉴를 파는 곳으로 보고, 아니면 '메뉴 확인 필요'로 구분한다.
def menu_match(query, document):
    menu = (query or '').replace(' ', '')
    if not menu:
        return False
    name = (document.get('place_name') or '').replace(' ', '')
    categories = [part.replace(' ', '') for part in (document.get('category_name') or '').split('>')]
    return menu in name or any(menu in part or (part not in GENERIC_CATEGORIES and len(part) >= 2 and part in menu)
                               for part in categories if part)


# query: 음식 종류(예: 샐러드), area: 지역명(예: 강남역), lat/lng: 현재 위치. 카카오 결과 15곳 중
# 메뉴가 일치하는 곳을 먼저(같은 그룹 안에서는 카카오 순서·가까운 순) 최대 size곳 돌려준다.
def search(query, area=None, lat=None, lng=None, size=5):
    if not api_key():
        raise PlacesUnavailable('missing key')
    keyword = ' '.join(part for part in (area, query or '맛집') if part)
    params = {'query': keyword[:100], 'category_group_code': 'FD6', 'size': 15}
    if lat is not None and lng is not None:
        params.update({'x': f'{lng:.6f}', 'y': f'{lat:.6f}', 'radius': 2000, 'sort': 'distance'})
    try:
        response = httpx.get(SEARCH_URL, params=params, headers={'Authorization': f'KakaoAK {api_key()}'}, timeout=10)
        response.raise_for_status()
        documents = response.json().get('documents') or []
    except Exception as error:
        logger.warning('kakao place search failed: %s', type(error).__name__)
        raise PlacesUnavailable(type(error).__name__) from error
    ranked = sorted(documents, key=lambda d: not menu_match(query, d))[:size]
    return [{'name': d.get('place_name', ''), 'category': (d.get('category_name') or '').split(' > ')[-1],
             'address': d.get('road_address_name') or d.get('address_name') or '',
             'distance': int(d['distance']) if str(d.get('distance') or '').isdigit() else None,
             'phone': d.get('phone') or '', 'url': d.get('place_url') or '',
             'lat': coordinate(d.get('y')), 'lng': coordinate(d.get('x')),
             'menu_match': menu_match(query, d)} for d in ranked]


# 카카오는 좌표를 문자열로 준다. 페이지 안 지도 표시용이며 값이 없거나 이상하면 None.
def coordinate(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
