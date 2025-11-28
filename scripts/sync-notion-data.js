/**
 * 아산시 스마트시티 자산관리 - 노션 데이터 동기화 스크립트
 * Slack #자산관리대장 -> Notion -> GitHub 연동
 * 
 * 환경변수:
 * - NOTION_API_KEY: 노션 API 통합 키
 * - NOTION_DATABASE_ID: 자산관리 마스터 DB ID
 */

const { Client } = require('@notionhq/client');
const fs = require('fs');
const path = require('path');

// 노션 클라이언트 초기화
const notion = new Client({
  auth: process.env.NOTION_API_KEY
});

// 데이터베이스 ID (자산관리 마스터 DB)
const DATABASE_ID = process.env.NOTION_DATABASE_ID || '2aa50aa9577d81ee9cd0e7e63b3fdf25';

// 데이터 저장 디렉토리
const DATA_DIR = path.join(__dirname, '..', 'data');

// 디렉토리 생성
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

/**
 * 노션 데이터베이스에서 모든 자산 데이터 가져오기
 */
async function fetchAllAssets() {
  console.log('📦 노션 자산관리 DB에서 데이터 동기화 시작...');
  console.log('   Database ID:', DATABASE_ID);
  
  const assets = [];
  let hasMore = true;
  let startCursor = undefined;
  
  while (hasMore) {
    const response = await notion.databases.query({
      database_id: DATABASE_ID,
      start_cursor: startCursor,
      page_size: 100
    });
    
    for (const page of response.results) {
      const props = page.properties;
      
      const asset = {
        id: page.id,
        자산명: getTitle(props['자산명']),
        자산코드: getNumber(props['자산코드']),
        자산분류: getSelect(props['자산분류']),
        자산등급: getSelect(props['자산등급']),
        라이프사이클: getSelect(props['라이프사이클']),
        구매금액: getNumber(props['구매금액']),
        설치위치: getSelect(props['설치위치']),
        사용상태: getSelect(props['사용상태']),
        관리담당자: getSelect(props['관리담당자']),
        관련프로젝트: getSelect(props['관련프로젝트'])
      };
      
      assets.push(asset);
    }
    
    hasMore = response.has_more;
    startCursor = response.next_cursor;
  }
  
  console.log(`✅ ${assets.length}개 자산 데이터 로드 완료`);
  return assets;
}

// 속성 값 추출 헬퍼 함수
function getTitle(prop) {
  if (!prop || prop.type !== 'title') return '';
  return prop.title.map(t => t.plain_text).join('');
}

function getNumber(prop) {
  if (!prop || prop.type !== 'number') return null;
  return prop.number;
}

function getSelect(prop) {
  if (!prop || prop.type !== 'select') return null;
  return prop.select?.name || null;
}

/**
 * 카테고리별 통계 계산
 */
function calculateCategories(assets) {
  const categoryMap = {
    '영상음향장비': { name: '영상음향장비', value: 0, amount: 0, color: '#3B82F6', icon: '🎬' },
    '전시장비': { name: '전시장비', value: 0, amount: 0, color: '#10B981', icon: '🖼️' },
    '네트워크장비': { name: '네트워크장비', value: 0, amount: 0, color: '#F59E0B', icon: '📶' },
    'IT장비': { name: 'IT장비', value: 0, amount: 0, color: '#8B5CF6', icon: '💻' },
    '기타장비': { name: '기타장비', value: 0, amount: 0, color: '#8B5CF6', icon: '📦' }
  };
  
  assets.forEach(asset => {
    const category = asset.자산분류 || '기타장비';
    if (categoryMap[category]) {
      categoryMap[category].value++;
      categoryMap[category].amount += Math.round((asset.구매금액 || 0) / 10000); // 만원 단위
    }
  });
  
  return Object.values(categoryMap).filter(c => c.value > 0);
}

/**
 * 대형 인프라 프로젝트 데이터 (수동 관리 - 별도 DB 연동 가능)
 */
function getProjects() {
  return [
    { name: 'SDDC Platform', budget: 27, status: '기술협상', progress: 65, manager: '이성호', color: '#F59E0B' },
    { name: '유무선 네트워크', budget: 8, status: '계약완료', progress: 100, manager: '이성호', color: '#10B981' },
    { name: '디지털OASIS 정보관리', budget: 25, status: '기술협상', progress: 70, manager: '임혁', color: '#EF4444' },
    { name: 'AI통합관제 플랫폼', budget: 16, status: '협상준비', progress: 30, manager: '김주용', color: '#F59E0B' },
    { name: '디지털OASIS SPOT', budget: 35, status: '부지협의', progress: 25, manager: '임혁', color: '#F59E0B' }
  ];
}

/**
 * 신규 도입 예정 자산
 */
function getNewAssets() {
  return [
    { name: '서버랙 (펜디급)', qty: 4, amount: 2000, status: '발주완료', priority: 'high' },
    { name: '네트워크랙', qty: 1, amount: 500, status: '발주완료', priority: 'high' },
    { name: 'POE 스위치', qty: 4, amount: 800, status: '납품대기', priority: 'medium' },
    { name: '5GHz WiFi AP', qty: 26, amount: 5200, status: '설치예정', priority: 'medium' },
    { name: '스마트폴', qty: 5, amount: 15000, status: '부지협의', priority: 'medium' },
    { name: 'ESS (에너지저장)', qty: 1, amount: 5000, status: '사양검토', priority: 'low' }
  ];
}

/**
 * 메인 실행 함수
 */
async function main() {
  console.log('========================================');
  console.log('🚀 아산시 자산관리 데이터 동기화 시작');
  console.log(`📅 실행 시간: ${new Date().toISOString()}`);
  console.log('========================================\n');
  
  try {
    // 1. 노션에서 자산 데이터 가져오기
    const assets = await fetchAllAssets();
    
    // 2. 카테고리 통계 계산
    const categories = calculateCategories(assets);
    
    // 3. 대형 프로젝트 및 신규 자산 데이터
    const projects = getProjects();
    const newAssets = getNewAssets();
    
    // 4. 대시보드 데이터 생성
    const dashboardData = {
      syncInfo: {
        lastSync: new Date().toISOString(),
        source: 'Notion API',
        database: DATABASE_ID,
        assetCount: assets.length,
        status: 'success'
      },
      projects: projects,
      newAssets: newAssets,
      categories: categories,
      // 기존 자산 목록 (필요시)
      assets: assets.slice(0, 20) // 최근 20개만
    };
    
    // 5. JSON 파일 저장
    const outputPath = path.join(DATA_DIR, 'dashboard-data.json');
    fs.writeFileSync(outputPath, JSON.stringify(dashboardData, null, 2), 'utf8');
    
    console.log('\n========================================');
    console.log('✅ 데이터 동기화 완료!');
    console.log(`📊 총 자산: ${assets.length}개`);
    console.log(`📁 저장 위치: ${outputPath}`);
    console.log('========================================');
    
  } catch (error) {
    console.error('❌ 동기화 오류:', error.message);
    
    // 오류 발생 시에도 기본 데이터 저장
    const fallbackData = {
      syncInfo: {
        lastSync: new Date().toISOString(),
        status: 'error',
        error: error.message
      },
      projects: getProjects(),
      newAssets: getNewAssets(),
      categories: [
        { name: '영상음향장비', value: 29, amount: 1450, color: '#3B82F6', icon: '🎬' },
        { name: '전시장비', value: 6, amount: 245, color: '#10B981', icon: '🖼️' },
        { name: '네트워크장비', value: 6, amount: 157, color: '#F59E0B', icon: '📶' },
        { name: '기타장비', value: 3, amount: 69, color: '#8B5CF6', icon: '📦' }
      ]
    };
    
    const outputPath = path.join(DATA_DIR, 'dashboard-data.json');
    fs.writeFileSync(outputPath, JSON.stringify(fallbackData, null, 2), 'utf8');
    console.log('⚠️ 기본 데이터로 저장됨');
    
    process.exit(1);
  }
}

// 실행
main();
