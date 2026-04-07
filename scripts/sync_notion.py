#!/usr/bin/env python3
"""
아산시 스마트시티 자산관리 Notion → GitHub Pages 동기화
Notion 📦 자산관리 마스터 DB → data/assets.json

v1.0 | 2026-04-07
"""

import json, os, urllib.request, urllib.error, time
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
NOTION_DB_ID = os.environ.get('NOTION_DB_ID', '2aa50aa9577d81ee9cd0e7e63b3fdf25')
NOTION_API = 'https://api.notion.com/v1'
KST = timezone(timedelta(hours=9))
OUTPUT_PATH = 'data/assets.json'

def notion_request(method, path, body=None):
    url = f'{NOTION_API}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {NOTION_TOKEN}')
    req.add_header('Notion-Version', '2022-06-28')
    req.add_header('Content-Type', 'application/json')

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 3 * (attempt + 1)
                print(f'  Rate limited, waiting {wait}s...')
                time.sleep(wait)
                continue
            body_text = e.read().decode() if e.fp else ''
            raise Exception(f'HTTP {e.code}: {body_text}')
    raise Exception('Max retries exceeded')

def extract_text(prop, prop_type):
    if not prop:
        return ''
    if prop_type == 'title':
        return ''.join(t.get('plain_text', '') for t in prop.get('title', []))
    if prop_type == 'rich_text':
        return ''.join(t.get('plain_text', '') for t in prop.get('rich_text', []))
    if prop_type == 'select':
        sel = prop.get('select')
        return sel.get('name', '') if sel else ''
    if prop_type == 'number':
        return prop.get('number')
    if prop_type == 'checkbox':
        return prop.get('checkbox', False)
    if prop_type == 'date':
        d = prop.get('date')
        if d:
            return {'start': d.get('start'), 'end': d.get('end')}
        return None
    if prop_type == 'auto_increment_id':
        uid = prop.get('unique_id', {})
        return uid.get('number')
    return None

def fetch_all_assets():
    """Notion DB에서 전체 자산 조회 (페이지네이션)"""
    assets = []
    cursor = None
    page = 0

    while True:
        page += 1
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor

        print(f'  Fetching page {page}...')
        data = notion_request('POST', f'/databases/{NOTION_DB_ID}/query', body)

        for item in data.get('results', []):
            p = item.get('properties', {})
            asset_name = extract_text(p.get('자산명'), 'title')

            if not asset_name or not asset_name.strip():
                continue

            asset = {
                'id': item['id'],
                'url': item['url'],
                '자산코드': extract_text(p.get('자산코드'), 'auto_increment_id'),
                '자산명': asset_name,
                '모델명': extract_text(p.get('모델명'), 'rich_text'),
                '자산분류': extract_text(p.get('자산분류'), 'select'),
                '세부분류': extract_text(p.get('세부분류'), 'select'),
                '자산등급': extract_text(p.get('자산등급'), 'select'),
                '제조사': extract_text(p.get('제조사'), 'rich_text'),
                '관리담당자': extract_text(p.get('관리담당자'), 'select'),
                '구매금액': extract_text(p.get('구매금액'), 'number'),
                '구매처': extract_text(p.get('구매처'), 'rich_text'),
                '구매일자': extract_text(p.get('구매일자'), 'date'),
                '사용상태': extract_text(p.get('사용상태'), 'select'),
                '설치위치': extract_text(p.get('설치위치'), 'select'),
                '사용부서': extract_text(p.get('사용부서'), 'select'),
                '라이프사이클': extract_text(p.get('라이프사이클'), 'select'),
                '관련프로젝트': extract_text(p.get('관련프로젝트'), 'select'),
                '시리얼번호': extract_text(p.get('시리얼번호'), 'rich_text'),
                '비고': extract_text(p.get('비고'), 'rich_text'),
                '보험가입여부': extract_text(p.get('보험가입여부'), 'checkbox'),
                '잔존가치': extract_text(p.get('잔존가치'), 'number'),
                '내용연수': extract_text(p.get('내용연수'), 'number'),
                '보증기간': extract_text(p.get('보증기간'), 'date'),
                '점검일정': extract_text(p.get('점검일정'), 'date'),
                'QR코드': extract_text(p.get('QR코드'), 'rich_text'),
            }
            assets.append(asset)

        if data.get('has_more') and data.get('next_cursor'):
            cursor = data['next_cursor']
            time.sleep(0.8)
        else:
            break

    return assets

def compute_summary(assets):
    """대시보드용 요약 통계 계산"""
    total = len(assets)
    total_value = sum(a.get('구매금액') or 0 for a in assets)

    # 상태별
    status_count = {}
    for a in assets:
        s = a.get('사용상태') or '미지정'
        status_count[s] = status_count.get(s, 0) + 1

    # 분류별
    category_count = {}
    category_value = {}
    for a in assets:
        c = a.get('자산분류') or '미분류'
        category_count[c] = category_count.get(c, 0) + 1
        category_value[c] = category_value.get(c, 0) + (a.get('구매금액') or 0)

    # 담당자별
    manager_count = {}
    for a in assets:
        m = a.get('관리담당자') or '미지정'
        manager_count[m] = manager_count.get(m, 0) + 1

    # 위치별
    location_count = {}
    for a in assets:
        loc = a.get('설치위치') or '미배치'
        location_count[loc] = location_count.get(loc, 0) + 1

    return {
        'total_assets': total,
        'total_value': total_value,
        'by_status': status_count,
        'by_category': category_count,
        'by_category_value': category_value,
        'by_manager': manager_count,
        'by_location': location_count,
    }

def main():
    if not NOTION_TOKEN:
        print('❌ NOTION_TOKEN 환경변수가 설정되지 않았습니다.')
        return

    print('=== 아산시 자산관리 Notion → JSON 동기화 ===')

    # 1. Notion에서 전체 자산 조회
    print('📦 Notion DB 조회 중...')
    assets = fetch_all_assets()
    print(f'  → {len(assets)}건 조회 완료')

    # 2. 비자산 항목 필터링 (Claude 링크, GitHub 링크 등)
    filtered = []
    skip_keywords = ['Claude', 'GitHub', 'LEESUNGHO-AI', 'Slack #']
    for a in assets:
        name = a.get('자산명', '')
        if any(kw in name for kw in skip_keywords):
            print(f'  ⏭️ 비자산 항목 스킵: {name}')
            continue
        if not name.strip():
            continue
        filtered.append(a)

    print(f'  → {len(filtered)}건 유효 자산')

    # 3. 요약 통계 계산
    summary = compute_summary(filtered)

    # 4. JSON 출력
    output = {
        'meta': {
            'synced_at': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST'),
            'source': 'Notion 📦 자산관리 마스터 DB',
            'notion_db': f'https://www.notion.so/{NOTION_DB_ID.replace("-", "")}',
            'version': '1.0',
        },
        'summary': summary,
        'assets': filtered,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'✅ {OUTPUT_PATH} 생성 완료 ({len(filtered)}건, {summary["total_value"]:,.0f}원)')

if __name__ == '__main__':
    main()
