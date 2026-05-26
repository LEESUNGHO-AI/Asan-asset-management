#!/usr/bin/env python3
"""
============================================================================
 아산시 강소형 스마트시티 — Notion 자산관리 마스터 DB → assets.json 동기화
 v1.2 (2026-05-26) — 표준자산코드 / QR URL / 발번일시 / 발번상태 4개 필드 추가
============================================================================
 실행 위치 : GitHub Actions (.github/workflows/sync-assets.yml)
 호출 주기 : 매 30분 (cron: */30 * * * *)
 출력 파일 : data/assets.json (146건 ≈ 150KB)

 [v1.2 변경 사항]
  + extract_text()에 'url' 타입 지원 추가
  + assets 배열에 다음 4개 필드 추가:
    - 표준자산코드 (text)   → ASAN-SC-U05-810-2025-0001
    - QR URL       (url)    → https://leesungho-ai.github.io/...
    - 발번일시     (date)   → 2026-05-22T03:45:00.000Z
    - 발번상태     (select) → 발번완료
  + meta.version "1.1" → "1.2"

 [의존 환경 변수]
  NOTION_TOKEN  : Notion Integration Secret (GitHub Actions Secret)
  NOTION_DB_ID  : 2aa50aa9577d81ee9cd0e7e63b3fdf25 (선택, 기본값 내장)
============================================================================
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

# ──────────────────────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
NOTION_DB_ID = os.environ.get('NOTION_DB_ID', '2aa50aa9577d81ee9cd0e7e63b3fdf25')
NOTION_VERSION = '2022-06-28'
OUTPUT_PATH = 'data/assets.json'

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json',
}

# ──────────────────────────────────────────────────────────────────────────
# Notion property 값 추출 (모든 타입 지원)
# ──────────────────────────────────────────────────────────────────────────
def extract_text(prop, ptype):
    """Notion property 객체에서 실제 값을 추출. 타입별 분기 처리."""
    if not prop:
        return None

    if ptype == 'rich_text':
        items = prop.get('rich_text') or []
        return ''.join(t.get('plain_text', '') for t in items)

    if ptype == 'title':
        items = prop.get('title') or []
        return ''.join(t.get('plain_text', '') for t in items)

    if ptype == 'select':
        sel = prop.get('select')
        return sel.get('name') if sel else None

    if ptype == 'multi_select':
        items = prop.get('multi_select') or []
        return [t.get('name') for t in items]

    if ptype == 'date':
        d = prop.get('date')
        if not d:
            return None
        return {'start': d.get('start'), 'end': d.get('end')}

    if ptype == 'number':
        return prop.get('number')

    if ptype == 'checkbox':
        return bool(prop.get('checkbox'))

    if ptype == 'url':                                          # ✨ v1.2 추가
        return prop.get('url')

    if ptype == 'email':
        return prop.get('email')

    if ptype == 'phone_number':
        return prop.get('phone_number')

    if ptype == 'people':
        items = prop.get('people') or []
        return [p.get('name') for p in items if p.get('name')]

    if ptype == 'files':
        items = prop.get('files') or []
        return [f.get('name', '') for f in items]

    if ptype == 'unique_id' or ptype == 'auto_increment_id':
        uid = prop.get('unique_id') or prop.get('auto_increment_id')
        if uid:
            return uid.get('number')
        return None

    if ptype == 'created_time':
        return prop.get('created_time')

    if ptype == 'last_edited_time':
        return prop.get('last_edited_time')

    return None


# ──────────────────────────────────────────────────────────────────────────
# Notion DB 전체 조회 (페이지네이션)
# ──────────────────────────────────────────────────────────────────────────
def fetch_all_assets():
    url = f'https://api.notion.com/v1/databases/{NOTION_DB_ID}/query'
    assets = []
    cursor = None

    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor

        res = requests.post(url, headers=HEADERS, json=body, timeout=30)
        if res.status_code != 200:
            raise RuntimeError(f'Notion API HTTP {res.status_code}: {res.text[:300]}')

        data = res.json()

        for page in data.get('results', []):
            p = page.get('properties', {})

            # ── 자산코드: auto_increment_id 타입 (Notion 자동 번호) ─────────
            asset_code_num = None
            asset_code_prop = p.get('자산코드')
            if asset_code_prop:
                if asset_code_prop.get('type') == 'unique_id':
                    asset_code_num = (asset_code_prop.get('unique_id') or {}).get('number')
                elif asset_code_prop.get('type') == 'auto_increment_id':
                    asset_code_num = (asset_code_prop.get('auto_increment_id') or {}).get('number')

            asset = {
                'id': page.get('id'),
                'url': page.get('url'),

                # ── 기존 필드 ────────────────────────────────────────────
                '자산코드':     asset_code_num,
                '자산명':       extract_text(p.get('자산명'),       'title'),
                '모델명':       extract_text(p.get('모델명'),       'rich_text'),
                '자산분류':     extract_text(p.get('자산분류'),     'select'),
                '세부분류':     extract_text(p.get('세부분류'),     'select'),
                '자산등급':     extract_text(p.get('자산등급'),     'select'),
                '제조사':       extract_text(p.get('제조사'),       'rich_text'),
                '관리담당자':   extract_text(p.get('관리담당자'),   'select'),
                '구매금액':     extract_text(p.get('구매금액'),     'number'),
                '구매처':       extract_text(p.get('구매처'),       'rich_text'),
                '구매일자':     extract_text(p.get('구매일자'),     'date'),
                '사용상태':     extract_text(p.get('사용상태'),     'select'),
                '설치위치':     extract_text(p.get('설치위치'),     'select'),
                '사용부서':     extract_text(p.get('사용부서'),     'select'),
                '라이프사이클': extract_text(p.get('라이프사이클'), 'select'),
                '관련프로젝트': extract_text(p.get('관련프로젝트'), 'select'),
                '시리얼번호':   extract_text(p.get('시리얼번호'),   'rich_text'),
                '비고':         extract_text(p.get('비고'),         'rich_text'),
                '보험가입여부': extract_text(p.get('보험가입여부'), 'checkbox'),
                '잔존가치':     extract_text(p.get('잔존가치'),     'number'),
                '내용연수':     extract_text(p.get('내용연수'),     'number'),
                '보증기간':     extract_text(p.get('보증기간'),     'date'),
                '점검일정':     extract_text(p.get('점검일정'),     'date'),
                'QR코드':       extract_text(p.get('QR코드'),       'rich_text'),

                # ── v1.2 신규 4개 필드 ───────────────────────────────────
                '표준자산코드': extract_text(p.get('표준자산코드'), 'rich_text'),
                'QR URL':       extract_text(p.get('QR URL'),       'url'),
                '발번일시':     extract_text(p.get('발번일시'),     'date'),
                '발번상태':     extract_text(p.get('발번상태'),     'select'),
            }
            assets.append(asset)

        if data.get('has_more') and data.get('next_cursor'):
            cursor = data['next_cursor']
            time.sleep(0.8)  # Rate limit 회피
        else:
            break

    return assets


# ──────────────────────────────────────────────────────────────────────────
# 요약 통계 (v1.2: 발번률 추가)
# ──────────────────────────────────────────────────────────────────────────
def compute_summary(assets):
    total = len(assets)
    total_value = sum(a.get('구매금액') or 0 for a in assets)

    status_count = {}
    category_count = {}
    category_value = {}
    manager_count = {}
    location_count = {}
    unit_count = {}                              # ✨ v1.2: 단위사업별 집계

    issued_count = 0                             # ✨ v1.2: 발번 완료 자산 수
    pending_count = 0                            # ✨ v1.2: 미발번 자산 수

    for a in assets:
        s = a.get('사용상태') or '미지정'
        status_count[s] = status_count.get(s, 0) + 1

        c = a.get('자산분류') or '미분류'
        category_count[c] = category_count.get(c, 0) + 1
        category_value[c] = category_value.get(c, 0) + (a.get('구매금액') or 0)

        m = a.get('관리담당자') or '미지정'
        manager_count[m] = manager_count.get(m, 0) + 1

        loc = a.get('설치위치') or '미배치'
        location_count[loc] = location_count.get(loc, 0) + 1

        # 발번 통계 + 단위사업 추출
        std_code = a.get('표준자산코드') or ''
        if std_code:
            issued_count += 1
            # ASAN-SC-U05-810-2025-0001 형식에서 U## 추출
            parts = std_code.split('-')
            if len(parts) >= 3 and parts[2].startswith('U'):
                unit = parts[2]
                unit_count[unit] = unit_count.get(unit, 0) + 1
        else:
            pending_count += 1

    return {
        'total_assets': total,
        'total_value': total_value,
        'by_status': status_count,
        'by_category': category_count,
        'by_category_value': category_value,
        'by_manager': manager_count,
        'by_location': location_count,
        'by_unit': unit_count,                   # ✨ v1.2
        'issued_count': issued_count,            # ✨ v1.2
        'pending_count': pending_count,          # ✨ v1.2
        'issued_rate': round(issued_count / total * 100, 1) if total > 0 else 0,
    }


# ──────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────
def main():
    if not NOTION_TOKEN:
        print('❌ NOTION_TOKEN 환경변수가 설정되지 않았습니다.')
        print('GitHub: Settings → Secrets and variables → Actions → New repository secret')
        print('Name: NOTION_TOKEN / Value: ntn_...')
        sys.exit(1)

    print('=== 아산시 자산관리 Notion → JSON 동기화 v1.2 ===')
    print(f'DB ID: {NOTION_DB_ID}')
    print(f'Token: {NOTION_TOKEN[:12]}...')

    # 1. Notion 전체 자산 조회
    print('\n📦 Notion DB 조회 중...')
    try:
        assets = fetch_all_assets()
    except Exception as e:
        print(f'❌ Notion API 오류: {e}')
        sys.exit(1)
    print(f'  → {len(assets)}건 조회 완료')

    # 2. 비자산 항목 필터링
    filtered = []
    skip_keywords = ['Claude', 'GitHub', 'LEESUNGHO-AI', 'Slack #']
    for a in assets:
        name = a.get('자산명') or ''
        if any(kw in name for kw in skip_keywords):
            print(f'  ⏭️  스킵: {name}')
            continue
        if not name.strip():
            continue
        filtered.append(a)
    print(f'  → {len(filtered)}건 유효 자산')

    # 3. 요약 통계
    summary = compute_summary(filtered)
    print(f'  → 발번 완료: {summary["issued_count"]} / 미발번: {summary["pending_count"]} '
          f'(발번률 {summary["issued_rate"]}%)')

    # 4. JSON 출력
    output = {
        'meta': {
            'synced_at': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST'),
            'source': 'Notion 자산관리 마스터 DB',
            'notion_db': f'https://www.notion.so/{NOTION_DB_ID.replace("-", "")}',
            'version': '1.2',
        },
        'summary': summary,
        'assets': filtered,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH) or '.', exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n✅ {OUTPUT_PATH} 생성 완료 ({len(filtered)}건, ₩{summary["total_value"]:,.0f})')
    print(f'   표준자산코드 부여: {summary["issued_count"]}건 / 단위사업: {summary["by_unit"]}')


if __name__ == '__main__':
    main()
