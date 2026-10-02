"""Authenticated QA client. Never connects directly to the database."""
import os
import sys
from pathlib import Path
import requests
import streamlit as st

st.set_page_config(page_title='CaloDetect 관리자 QA', layout='wide')
st.title('CaloDetect 관리자 QA')
base = os.environ.get('CALODETECT_API_URL', 'http://127.0.0.1:8000').rstrip('/')


def call(method, path, **kwargs):
    token = st.session_state.get('qa_token')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    response = requests.request(method, base + path, headers=headers, timeout=30, **kwargs)
    if not response.ok:
        try:
            message = response.json().get('error', {}).get('message', 'API 요청 실패')
        except ValueError:
            message = 'API 응답을 확인하세요.'
        raise RuntimeError(message)
    return response


if not st.session_state.get('qa_token'):
    with st.form('admin_login'):
        email = st.text_input('관리자 이메일')
        password = st.text_input('비밀번호', type='password')
        submitted = st.form_submit_button('관리자 로그인')
    if submitted:
        try:
            login_response = call('POST', '/auth/login', json={'email':email,'password':password})
            result = login_response.json()
            if result['user']['role'] != 'admin':
                # Revoke the issued session even for a rejected ordinary user.
                requests.post(base+'/auth/logout',cookies=login_response.cookies,
                              headers={'X-CSRF-Token':result['csrf_token']},timeout=10)
                st.error('관리자 계정만 접근할 수 있습니다.')
            else:
                st.session_state.qa_token = result['access_token']; st.rerun()
        except (requests.RequestException, RuntimeError) as error:
            st.error(str(error))
else:
    if st.button('로그아웃'):
        # The auth route uses cookie + CSRF. Fetch session CSRF through a cookie request.
        token = st.session_state.qa_token
        try:
            session = requests.get(base+'/users/me',cookies={'calodetect_session':token},timeout=10).json()
            requests.post(base+'/auth/logout',cookies={'calodetect_session':token},
                          headers={'X-CSRF-Token':session['csrf_token']},timeout=10)
        finally:
            st.session_state.pop('qa_token',None); st.rerun()
    try:
        rows = call('GET','/admin/retraining/samples').json()['items']
        if not rows:
            st.info('검수할 샘플이 없습니다.')
        for item in rows:
            with st.container(border=True):
                st.write(f"{item['predicted_label']} → {item['corrected_label']} · {item['qa_status']}")
                try:
                    picture = call('GET',f"/admin/retraining/samples/{item['id']}/image").content
                    st.image(picture, width=350)
                except RuntimeError as error:
                    st.warning(str(error))
                if item['qa_status'] == 'PENDING':
                    approve, reject = st.columns(2)
                    for column, action, label in [(approve,'approve','승인'),(reject,'reject','거절')]:
                        if column.button(label,key=f"{action}_{item['id']}"):
                            call('POST',f"/admin/retraining/samples/{item['id']}/{action}")
                            st.rerun()
    except (requests.RequestException, RuntimeError) as error:
        st.error(str(error))
