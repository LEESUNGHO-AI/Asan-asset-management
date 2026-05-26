#!/usr/bin/env python3
"""
============================================================================
 아산시 강소형 스마트시티 — Notion 자산관리 마스터 DB → assets.json 동기화
 v1.3 (2026-05-26) — 자가 진단 강화 (exit code 1 원인 명확 출력)
============================================================================

 [v1.3 개선 사항]
  + 5단계 자가 진단 로그 — 어디서 죽었는지 즉시 식별 가능
  + Notion API 응답 타입을 동적으로 감지 (unique_id / auto_increment_id 양쪽)
  + 4개 신규 필드 추출 (표준자산코드 / QR URL / 발번일시 / 발번상태)
  + 모든 예외에 명확한 한국어 에러 메시지 + 해결 방법 출력

 [실패 시 확인 사항]
  STEP 1 실패 → NOTION_TOKEN secret 설정 확인
  STEP 2 실패 → requests 라이브러리 설치 확인 (워크플로우 yml에 pip install)
  STEP 3 실패 → NOTION_DB_ID 또는 토큰 권한 확인
  STEP 4 실패 → Notion 페이지 properties 구조 변경 확인
  STEP 5 실패 → data/ 디렉토리 쓰기 권한 확인
============================================================================
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────────────────────────────────────
# STEP 0: 의존성 체크 — requests 임포트 실패 시 명확한 메시지
# ──────────────────────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print('=' * 60, flush=True)
    print('❌ FATAL: requests 라이브러리가 설치되지 않았습니다.', flush=True)
    print('=' * 60, flush=True)
    print('GitHub Actions 워크플로우 yml에 다음 단계를 추가하세요:', flush=True)
    print('    - name: Install dependencies', flush=True)
    print('      run: pip install requests', flush=True)
    sys.exit(1)

KST = timezone(timedelta(hours=9))
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '').strip()
NOTION_DB_ID = os.environ.get('NOTION_DB_ID', '2aa50aa9577d81ee9cd0e7e63b3fdf25').strip()
NOTION_VERSION = '2022-06-28'
OUTPUT_PATH = 'data/assets.json'


def check_env():
    print('━' * 60, flush=True)
    print('  STEP 1: 환경 변수 검증', flush=True)
    print('━' * 60, flush=True)
    if not NOTION_TOKEN:
        print('❌ NOTION_TOKEN 환경 변수가 비어 있습니다.', flush=True)
        print('해결: Settings → Secrets and variables → Actions → New secret', flush=True)
        print('      Name=NOTION_TOKEN / Value=ntn_...', flush=True)
        sys.exit(1)
    print(f'  ✓ NOTION_TOKEN  : {NOTION_TOKEN[:12]}... ({len(NOTION_TOKEN)} chars)', flush=True)
    print(f'  ✓ NOTION_DB_ID  : {NOTION_DB_ID}', flush=True)
    print(f'  ✓ Python ver    : {sys.version.split()[0]}', flush=True)
    print(f'  ✓ requests ver  : {requests.__version__}', flush=True)
    print('', flush=True)


def check_notion_connection():
    print('━' * 60, flush=True)
    print('  STEP 2: Notion API 연결 + 필드 점검', flush=True)
    print('━' * 60, flush=True)
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': NOTION_VERSION,
    }
    try:
        res = requests.get(f'https://api.notion.com/v1/databases/{NOTION_DB_ID}',
                           headers=headers, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f'❌ Notion API 호출 실패: {e}', flush=True)
        sys.exit(1)

    if res.status_code == 401:
        print('❌ Notion 인증 실패 (401) — NOTION_TOKEN 확인', flush=True)
        sys.exit(1)
    if res.status_code == 404:
        print(f'❌ Notion DB 미발견 (404) — DB ID 또는 Integration 권한 확인', flush=True)
        sys.exit(1)
    if res.status_code != 200:
        print(f'❌ HTTP {res.status_code}: {res.text[:300]}', flush=True)
        sys.exit(1)

    data = res.json()
    title = ''.join(t.get('plain_text', '') for t in data.get('title', []))
    print(f'  ✓ DB 연결 성공  : {title or "(제목 없음)"}', flush=True)

    props = data.get('properties', {})
    required = {
        '자산명':       'title',
        '표준자산코드': 'rich_text',
        'QR URL':       'url',
        '발번일시':     'date',
        '발번상태':     'select',
    }
    missing = []
    for name, expected_type in required.items():
        if name not in props:
            missing.append(f'{name} ({expected_type})')
        elif props[name].get('type') != expected_type:
            missing.append(f'{name} (현재: {props[name].get("type")}, 필요: {expected_type})')

    if missing:
        print('  ⚠️  필드 누락/불일치:', flush=True)
        for m in missing:
            print(f'     - {m}', flush=True)
    else:
        print('  ✓ 필수 필드 모두 존재 (5개)', flush=True)

    code_type = props.get('자산코드', {}).get('type', '?')
    print(f'  ✓ 자산코드 타입 : {code_type}', flush=True)
    print('', flush=True)


def extract_text(prop, ptype):
    if not prop:
        return None
    if ptype == 'rich_text':
        return ''.join(t.get('plain_text', '') for t in (prop.get('rich_text') or []))
    if ptype == 'title':
        return ''.join(t.get('plain_text', '') for t in (prop.get('title') or []))
    if ptype == 'select':
        sel = prop.get('select')
        return sel.get('name') if sel else None
    if ptype == 'date':
        d = prop.get('date')
        return {'start': d.get('start'), 'end': d.get('end')} if d else None
    if ptype == 'number':
        return prop.get('number')
    if ptype == 'checkbox':
        return bool(prop.get('checkbox'))
    if ptype == 'url':
        return prop.get('url')
    if ptype == 'people':
        return [p.get('name') for p in (prop.get('people') or []) if p.get('name')]
    if ptype == 'files':
        return [f.get('name', '') for f in (prop.get('files') or [])]
    return None


def extract_asset_code(prop):
    """자산코드(unique_id / auto_increment_id) 자동 감지"""
    if not prop:
        return None
    t = prop.get('type')
    if t == 'unique_id':
        return (prop.get('unique_id') or {}).get('number')
    if t == 'auto_increment_id':
        return (prop.get('auto_increment_id') or {}).get('number')
    uid = prop.get('unique_id') or prop.get('auto_increment_id')
    return uid.get('number') if uid else None


def fetch_all_assets():
    print('━' * 60, flush=True)
    print('  STEP 3: Notion DB 전체 조회', flush=True)
    print('━' * 60, flush=True)
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }
    url = f'https://api.notion.com/v1/databases/{NOTION_DB_ID}/query'
    assets = []
    cursor = None
    page_idx = 0

    while True:
        page_idx += 1
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor

        try:
            res = requests.post(url, headers=headers, json=body, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f'❌ Notion query 네트워크 오류: {e}', flush=True)
            sys.exit(1)

        if res.status_code != 200:
            print(f'❌ Notion query HTTP {res.status_code}: {res.text[:400]}', flush=True)
            sys.exit(1)

        data = res.json()
        page_results = data.get('results', [])
        print(f'  ✓ 페이지 {page_idx}: {len(page_results)}건', flush=True)

        for page in page_results:
            p = page.get('properties', {})
            asset = {
                'id': page.get('id'),
                'url': page.get('url'),
                '자산코드':     extract_asset_code(p.get('자산코드')),
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
                # v1.3 신규
                '표준자산코드': extract_text(p.get('표준자산코드'), 'rich_text'),
                'QR URL':       extract_text(p.get('QR URL'),       'url'),
                '발번일시':     extract_text(p.get('발번일시'),     'date'),
                '발번상태':     extract_text(p.get('발번상태'),     'select'),
            }
            assets.append(asset)

        if data.get('has_more') and data.get('next_cursor'):
            cursor = data['next_cursor']
            time.sleep(0.8)
        else:
            break

    print(f'  ✓ 전체 {len(assets)}건 조회', flush=True)
    print('', flush=True)
    return assets


def compute_summary(assets):
    total = len(assets)
    total_value = sum(a.get('구매금액') or 0 for a in assets)
    status_count, category_count, category_value = {}, {}, {}
    manager_count, location_count, unit_count = {}, {}, {}
    issued = pending = 0

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

        code = a.get('표준자산코드') or ''
        if code:
            issued += 1
            parts = code.split('-')
            if len(parts) >= 3 and parts[2].startswith('U'):
                unit_count[parts[2]] = unit_count.get(parts[2], 0) + 1
        else:
            pending += 1

    return {
        'total_assets': total,
        'total_value': total_value,
        'by_status': status_count,
        'by_category': category_count,
        'by_category_value': category_value,
        'by_manager': manager_count,
        'by_location': location_count,
        'by_unit': unit_count,
        'issued_count': issued,
        'pending_count': pending,
        'issued_rate': round(issued / total * 100, 1) if total > 0 else 0,
    }


def write_output(assets, summary):
    print('━' * 60, flush=True)
    print('  STEP 4: JSON 출력', flush=True)
    print('━' * 60, flush=True)
    output = {
        'meta': {
            'synced_at': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST'),
            'source': 'Notion 자산관리 마스터 DB',
            'notion_db': f'https://www.notion.so/{NOTION_DB_ID.replace("-", "")}',
            'version': '1.3',
        },
        'summary': summary,
        'assets': assets,
    }
    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH) or '.', exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f'❌ 파일 쓰기 실패: {e}', flush=True)
        sys.exit(1)
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f'  ✓ {OUTPUT_PATH} ({size_kb:.1f} KB)', flush=True)
    print('', flush=True)


def main():
    print('\n╔' + '═' * 58 + '╗', flush=True)
    print('║  아산시 자산관리 Notion → JSON 동기화 v1.3 (진단강화)    ║', flush=True)
    print('╚' + '═' * 58 + '╝\n', flush=True)

    try:
        check_env()
        check_notion_connection()
        assets = fetch_all_assets()

        print('━' * 60, flush=True)
        print('  비자산 항목 필터링', flush=True)
        print('━' * 60, flush=True)
        filtered = []
        skip = ['Claude', 'GitHub', 'LEESUNGHO-AI', 'Slack #']
        for a in assets:
            name = a.get('자산명') or ''
            if any(kw in name for kw in skip):
                print(f'  ⏭️  스킵: {name}', flush=True)
                continue
            if not name.strip():
                continue
            filtered.append(a)
        print(f'  ✓ 유효 자산 {len(filtered)}건\n', flush=True)

        summary = compute_summary(filtered)
        write_output(filtered, summary)

        print('━' * 60, flush=True)
        print('  최종 결과', flush=True)
        print('━' * 60, flush=True)
        print(f'  총 자산        : {summary["total_assets"]}건', flush=True)
        print(f'  총 자산가치    : ₩{summary["total_value"]:,.0f}', flush=True)
        print(f'  발번 완료      : {summary["issued_count"]}건', flush=True)
        print(f'  미발번         : {summary["pending_count"]}건', flush=True)
        print(f'  발번률         : {summary["issued_rate"]}%', flush=True)
        print(f'  단위사업 분포  : {summary["by_unit"]}', flush=True)
        print('\n✅ 동기화 완료\n', flush=True)
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        print('\n' + '❌' * 30, flush=True)
        print(f'❌ 예상치 못한 오류: {type(e).__name__}: {e}', flush=True)
        print('❌' * 30, flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
