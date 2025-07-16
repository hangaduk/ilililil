# scraper.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 사용자 설정: 여기에 관리할 모든 자사몰 정보를 추가하세요 ---
LOGIN_INFO = {
    "gcnong": {"id": "rootx", "pw": "aa1707aa"},    
    "wandoman": {"id": "rootx", "pw": "aa1707aa"},  
    "susanchon": {"id": "rootx", "pw": "aa1707aa"},  
    "hadonggol": {"id": "rootx", "pw": "aa1707aa"},  
    "hnhwangtogol": {"id": "rootx", "pw": "aa1707aa"},  
    "hcnong": {"id": "rootx", "pw": "aa1707aa"},  
    "suhofarm": {"id": "rootx", "pw": "aa1707aa"},  
    "youngheefarm": {"id": "rootx", "pw": "aa1707aa"},  
    "seongjunong": {"id": "rootx", "pw": "aa1707aa"},  
    # ... 이런 식으로 10개까지 계속 추가하시면 됩니다.
    # "사이트주소의고유한부분": {"id": "아이디", "pw": "비밀번호"},
}

# --- Firebase 인증 ---
key_content_str = os.environ.get('FIREBASE_KEY_JSON', '{}')
key_content_json = json.loads(key_content_str)

if not firebase_admin._apps:
    cred = credentials.Certificate(key_content_json)
    firebase_admin.initialize_app(cred)
db = firestore.client()

def clean_data(text):
    try:
        if not text or not text.strip(): return 0
        cleaned_text = text.replace(',', '').replace('%', '').strip()
        return int(cleaned_text) if '.' not in cleaned_text else float(cleaned_text)
    except (ValueError, AttributeError): return 0

def scrape_site_data(site_name, credentials):
    print(f"-> '{site_name}' 처리 시작...")
    base_url = f"https://{site_name}.com/root"
    try:
        with requests.Session() as s:
            login_res = s.post(f"{base_url}/login.php", data={'a': 'login', 'id': credentials['id'], 'pw': credentials['pw']}, verify=False, timeout=30)
            login_res.encoding = 'euc-kr'
            if "아이디 또는 비밀번호" in login_res.text:
                print(f"[실패] '{site_name}' 로그인 실패.")
                return None
            target_res = s.get(f"{base_url}/shop.state.main.php", verify=False, timeout=30)
            target_res.encoding = 'euc-kr'
            soup = BeautifulSoup(target_res.text, 'lxml')
            title_tag = soup.find('b', string='일별 매출분석')
            if not title_tag: return None
            today_str = f"{datetime.now().day:02d}일"
            rows = title_tag.find_parent('table').find_next_sibling('table').find_all('tr')
            todays_data_row = next((r.find_all('td') for r in rows[1:-1] if r.find('td') and r.find('td').text.strip().startswith(today_str)), None)
            if not todays_data_row: return {'주문건수': 0, '매출액': 0, '매입액': 0, '순익': 0, '마진': 0}
            result = {'주문건수': clean_data(todays_data_row[1].text),'매출액': clean_data(todays_data_row[7].text),'매입액': clean_data(todays_data_row[8].text),'순익': clean_data(todays_data_row[9].text),'마진': clean_data(todays_data_row[10].text)}
            print(f"[성공] '{site_name}' 데이터 수집 완료.")
            return result
    except Exception as e:
        print(f"[오류] '{site_name}' 처리 중 오류: {e}")
        return None

def main():
    print("매출 데이터 수집을 시작합니다.")
    all_sites_data = {site: scrape_site_data(site, creds) for site, creds in LOGIN_INFO.items()}
    today_doc_name = datetime.now().strftime('%Y-%m-%d')
    doc_ref = db.collection('daily_sales').document(today_doc_name)
    doc_ref.set(all_sites_data)
    print(f"\nFirestore에 '{today_doc_name}' 이름으로 데이터 저장 완료!")

if __name__ == '__main__':
    main()