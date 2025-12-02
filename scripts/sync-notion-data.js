#!/usr/bin/env node
/**
 * 아산시 스마트시티 자산관리 시스템 - Notion 데이터 동기화
 * 
 * 이 스크립트는 Notion 자산관리 마스터 DB에서 데이터를 가져와
 * GitHub Pages 대시보드용 JSON 파일로 저장합니다.
 * 
 * 데이터 흐름: Slack #자산관리대장 → Notion DB → GitHub Pages
 * 
 * @author Danny (제일엔지니어링 PMO)
 * @version 4.0.0
 */

const { Client } = require('@notionhq/client');
const fs = require('fs');
const path = require('path');

// 환경변수 로드
require('dotenv').config();

// Notion 클라이언트 초기화
const notion = new Client({
  auth: process.env.NOTION_API_KEY,
});

// 자산관리 마스터 DB ID
const DATABASE_ID = process.env.NOTION_DATABASE_ID || '2aa50aa9577d81ee9cd0e7e63b3fdf25';

// 데이터 저장 경로
const DATA_DIR = path.join(__dirname, '..', 'data');

// 디렉토리 생성
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

/**
 * Notion 속성에서 값 추출
 */
function extractPropertyValue(property) {
  if (!property) return null;
  
  switch (property.type) {
    case 'title':
      return property.title?.map(t => t.plain_text).join('') || '';
    case 'rich_text':
      return property.rich_text?.map(t => t.plain_text).join('') || '';
    case 'number':
      return property.number;
    case 'select':
      return property.select?.name || null;
    case 'multi_select':
      return property.multi_select?.map(s => s.name) || [];
    case 'date':
      return property.date?.start || null;
    case 'checkbox':
      return property.checkbox;
    case 'url':
      return property.url;
    case 'email':
      return property.email;
    case 'phone_number':
      return property.phone_number;
    case 'formula':
      return property.formula?.[property.formula.type];
    case 'relation':
      return property.relation?.map(r => r.id) || [];
    case 'rollup':
      if (property.rollup?.type === 'array') {
        return property.rollup.array?.map(item => extractPropertyValue(item)) || [];
      }
      return property.rollup?.[property.rollup?.type];
    case 'status':
      return property.status?.name || null;
    case 'created_time':
      return property.created_time;
    case 'last_edited_time':
      return property.last_edited_time;
    case 'created_by':
      return property.created_by?.name || property.created_by?.id;
    case 'last_edited_by':
      return property.last_edited_by?.name || property.last_edited_by?.id;
    case 'files':
      return property.files?.map(f => f.file?.url || f.external?.url) || [];
    default:
      return null;
  }
}

/**
 * Notion 데이터베이스에서 모든 자산 데이터 가져오기
 */
async function fetchAllAssets() {
  console.log('📡 Notion 자산관리 DB에서 데이터 가져오는 중...');
  
  const assets = [];
  let hasMore = true;
  let startCursor = undefined;
  
  while (hasMore) {
    try {
      const response = await notion.databases.query({
        database_id: DATABASE_ID,
        start_cursor: startCursor,
        page_size: 100,
      });
      
      for (const page of response.results) {
        const properties = page.properties;
        
        // 자산 데이터 매핑 (Notion DB 스키마에 맞게 조정 필요)
        const asset = {
          id: page.id,
          // 기본 정보
          name: extractPropertyValue(properties['자산명'] || properties['Name'] || properties['이름']),
          assetCode: extractPropertyValue(properties['자산코드'] || properties['Asset Code'] || properties['코드']),
          category: extractPropertyValue(properties['카테고리'] || properties['Category'] || properties['분류']),
          subCategory: extractPropertyValue(properties['세부분류'] || properties['Sub Category']),
          
          // 수량 및 가치
          quantity: extractPropertyValue(properties['수량'] || properties['Quantity']) || 1,
          unitPrice: extractPropertyValue(properties['단가'] || properties['Unit Price']) || 0,
          totalValue: extractPropertyValue(properties['총액'] || properties['Total Value']) || 0,
          
          // 상태 정보
          status: extractPropertyValue(properties['상태'] || properties['Status']) || '운영중',
          condition: extractPropertyValue(properties['컨디션'] || properties['Condition']),
          
          // 담당 정보
          manager: extractPropertyValue(properties['담당자'] || properties['Manager']),
          department: extractPropertyValue(properties['담당부서'] || properties['Department']),
          location: extractPropertyValue(properties['위치'] || properties['Location']),
          
          // 날짜 정보
          purchaseDate: extractPropertyValue(properties['구매일'] || properties['Purchase Date']),
          warrantyExpiry: extractPropertyValue(properties['보증만료일'] || properties['Warranty Expiry']),
          expectedDelivery: extractPropertyValue(properties['도입예정일'] || properties['Expected Delivery']),
          
          // 공급업체 정보
          supplier: extractPropertyValue(properties['공급업체'] || properties['Supplier']),
          manufacturer: extractPropertyValue(properties['제조사'] || properties['Manufacturer']),
          
          // 프로젝트 연관
          project: extractPropertyValue(properties['연관프로젝트'] || properties['Project']),
          priority: extractPropertyValue(properties['우선순위'] || properties['Priority']),
          
          // 메타 정보
          notes: extractPropertyValue(properties['비고'] || properties['Notes']),
          tags: extractPropertyValue(properties['태그'] || properties['Tags']) || [],
          
          // 시스템 정보
          createdAt: page.created_time,
          updatedAt: page.last_edited_time,
          notionUrl: page.url,
        };
        
        assets.push(asset);
      }
      
      hasMore = response.has_more;
      startCursor = response.next_cursor;
      
    } catch (error) {
      console.error('❌ Notion API 오류:', error.message);
      throw error;
    }
  }
  
  console.log(`✅ 총 ${assets.length}개 자산 데이터 로드 완료`);
  return assets;
}

/**
 * 통계 데이터 계산
 */
function calculateStatistics(assets) {
  const stats = {
    totalAssets: assets.length,
    totalValue: 0,
    byCategory: {},
    byManager: {},
    byStatus: {},
    byProject: {},
    warrantyActive: 0,
    warrantyExpired: 0,
    recentlyAdded: 0,
    upcomingDeliveries: 0,
  };
  
  const today = new Date();
  const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
  
  for (const asset of assets) {
    // 총 가치 계산
    const value = asset.totalValue || (asset.unitPrice * (asset.quantity || 1)) || 0;
    stats.totalValue += value;
    
    // 카테고리별 집계
    const category = asset.category || '미분류';
    if (!stats.byCategory[category]) {
      stats.byCategory[category] = { count: 0, value: 0 };
    }
    stats.byCategory[category].count++;
    stats.byCategory[category].value += value;
    
    // 담당자별 집계
    const manager = asset.manager || '미지정';
    if (!stats.byManager[manager]) {
      stats.byManager[manager] = { count: 0, value: 0 };
    }
    stats.byManager[manager].count++;
    stats.byManager[manager].value += value;
    
    // 상태별 집계
    const status = asset.status || '미확인';
    if (!stats.byStatus[status]) {
      stats.byStatus[status] = { count: 0, value: 0 };
    }
    stats.byStatus[status].count++;
    stats.byStatus[status].value += value;
    
    // 프로젝트별 집계
    const project = asset.project || '일반';
    if (!stats.byProject[project]) {
      stats.byProject[project] = { count: 0, value: 0 };
    }
    stats.byProject[project].count++;
    stats.byProject[project].value += value;
    
    // 보증기간 체크
    if (asset.warrantyExpiry) {
      const warrantyDate = new Date(asset.warrantyExpiry);
      if (warrantyDate > today) {
        stats.warrantyActive++;
      } else {
        stats.warrantyExpired++;
      }
    }
    
    // 최근 추가 (30일 이내)
    if (asset.createdAt) {
      const createdDate = new Date(asset.createdAt);
      if (createdDate > thirtyDaysAgo) {
        stats.recentlyAdded++;
      }
    }
    
    // 도입 예정
    if (asset.expectedDelivery) {
      const deliveryDate = new Date(asset.expectedDelivery);
      if (deliveryDate > today) {
        stats.upcomingDeliveries++;
      }
    }
  }
  
  return stats;
}

/**
 * 대형 인프라 프로젝트 데이터 생성
 */
function extractInfraProjects(assets) {
  const projectNames = ['SDDC', '네트워크', 'AI관제', '데이터허브', '통합플랫폼', '보안시스템'];
  const projects = [];
  
  for (const projectName of projectNames) {
    const projectAssets = assets.filter(a => 
      a.project?.includes(projectName) || 
      a.category?.includes(projectName) ||
      a.name?.includes(projectName)
    );
    
    if (projectAssets.length > 0) {
      const totalBudget = projectAssets.reduce((sum, a) => sum + (a.totalValue || 0), 0);
      const completedAssets = projectAssets.filter(a => 
        a.status === '운영중' || a.status === '완료' || a.status === '도입완료'
      );
      
      projects.push({
        name: projectName,
        totalAssets: projectAssets.length,
        completedAssets: completedAssets.length,
        progress: projectAssets.length > 0 
          ? Math.round((completedAssets.length / projectAssets.length) * 100) 
          : 0,
        budget: totalBudget,
        status: completedAssets.length === projectAssets.length ? '완료' : '진행중',
      });
    }
  }
  
  return projects;
}

/**
 * 도입 예정 자산 추출
 */
function extractUpcomingAssets(assets) {
  const today = new Date();
  
  return assets
    .filter(a => a.expectedDelivery && new Date(a.expectedDelivery) > today)
    .sort((a, b) => new Date(a.expectedDelivery) - new Date(b.expectedDelivery))
    .slice(0, 10)
    .map(a => ({
      name: a.name,
      category: a.category,
      expectedDate: a.expectedDelivery,
      value: a.totalValue || a.unitPrice,
      supplier: a.supplier,
    }));
}

/**
 * 리스크 데이터 추출
 */
function extractRisks(assets) {
  const risks = [];
  const today = new Date();
  const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
  
  for (const asset of assets) {
    // 보증 만료 임박
    if (asset.warrantyExpiry) {
      const warrantyDate = new Date(asset.warrantyExpiry);
      if (warrantyDate < today) {
        risks.push({
          type: 'warranty_expired',
          severity: 'high',
          asset: asset.name,
          description: `보증기간 만료 (${asset.warrantyExpiry})`,
          action: '보증 연장 또는 유지보수 계약 검토',
        });
      } else if (warrantyDate < thirtyDaysFromNow) {
        risks.push({
          type: 'warranty_expiring',
          severity: 'medium',
          asset: asset.name,
          description: `보증기간 만료 임박 (${asset.warrantyExpiry})`,
          action: '보증 연장 준비',
        });
      }
    }
    
    // 상태 이상
    if (asset.status === '점검필요' || asset.status === '수리중' || asset.condition === '불량') {
      risks.push({
        type: 'maintenance',
        severity: asset.status === '수리중' ? 'high' : 'medium',
        asset: asset.name,
        description: `자산 상태: ${asset.status || asset.condition}`,
        action: '유지보수 조치 필요',
      });
    }
  }
  
  // 심각도 순 정렬
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  risks.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
  
  return risks.slice(0, 20);
}

/**
 * 예산 데이터 생성
 */
function calculateBudget(assets, stats) {
  // 전체 예산 (하드코딩 - 실제값으로 교체 필요)
  const totalBudget = 24000000000; // 240억
  const executedBudget = stats.totalValue;
  
  return {
    total: totalBudget,
    executed: executedBudget,
    remaining: totalBudget - executedBudget,
    executionRate: Math.round((executedBudget / totalBudget) * 100 * 10) / 10,
    byCategory: Object.entries(stats.byCategory).map(([name, data]) => ({
      name,
      budget: data.value,
      percentage: Math.round((data.value / totalBudget) * 100 * 10) / 10,
    })),
  };
}

/**
 * 메인 동기화 함수
 */
async function syncNotionData() {
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('🏙️  아산시 스마트시티 자산관리 시스템 - 데이터 동기화');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log(`📅 동기화 시작: ${new Date().toISOString()}`);
  console.log(`📊 Database ID: ${DATABASE_ID}`);
  console.log('───────────────────────────────────────────────────────────────');
  
  try {
    // 1. Notion에서 자산 데이터 가져오기
    const assets = await fetchAllAssets();
    
    // 2. 통계 계산
    console.log('📈 통계 데이터 계산 중...');
    const statistics = calculateStatistics(assets);
    
    // 3. 인프라 프로젝트 데이터
    console.log('🏗️  인프라 프로젝트 데이터 추출 중...');
    const infraProjects = extractInfraProjects(assets);
    
    // 4. 도입 예정 자산
    console.log('📦 도입 예정 자산 추출 중...');
    const upcomingAssets = extractUpcomingAssets(assets);
    
    // 5. 리스크 데이터
    console.log('⚠️  리스크 데이터 분석 중...');
    const risks = extractRisks(assets);
    
    // 6. 예산 데이터
    console.log('💰 예산 데이터 계산 중...');
    const budget = calculateBudget(assets, statistics);
    
    // 7. 동기화 정보
    const syncInfo = {
      lastSync: new Date().toISOString(),
      lastSyncKST: new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }),
      source: 'Notion API',
      databaseId: DATABASE_ID,
      totalRecords: assets.length,
      syncDuration: 0,
      status: 'success',
    };
    
    // 8. 파일 저장
    console.log('💾 데이터 파일 저장 중...');
    
    const files = {
      'assets.json': assets,
      'statistics.json': statistics,
      'infra-projects.json': infraProjects,
      'upcoming-assets.json': upcomingAssets,
      'risks.json': risks,
      'budget.json': budget,
      'sync-info.json': syncInfo,
    };
    
    for (const [filename, data] of Object.entries(files)) {
      const filepath = path.join(DATA_DIR, filename);
      fs.writeFileSync(filepath, JSON.stringify(data, null, 2), 'utf8');
      console.log(`  ✅ ${filename} 저장 완료`);
    }
    
    // 결과 출력
    console.log('───────────────────────────────────────────────────────────────');
    console.log('📊 동기화 결과 요약:');
    console.log(`   • 총 자산: ${statistics.totalAssets}개`);
    console.log(`   • 총 가치: ₩${(statistics.totalValue / 100000000).toFixed(1)}억`);
    console.log(`   • 카테고리: ${Object.keys(statistics.byCategory).length}개`);
    console.log(`   • 담당자: ${Object.keys(statistics.byManager).length}명`);
    console.log(`   • 리스크: ${risks.length}건`);
    console.log(`   • 도입 예정: ${upcomingAssets.length}건`);
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('✅ 동기화 완료!');
    
    return { success: true, stats: statistics };
    
  } catch (error) {
    console.error('═══════════════════════════════════════════════════════════════');
    console.error('❌ 동기화 실패:', error.message);
    console.error('═══════════════════════════════════════════════════════════════');
    
    // 에러 시에도 sync-info.json 업데이트
    const syncInfo = {
      lastSync: new Date().toISOString(),
      lastSyncKST: new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }),
      status: 'error',
      error: error.message,
    };
    fs.writeFileSync(
      path.join(DATA_DIR, 'sync-info.json'),
      JSON.stringify(syncInfo, null, 2),
      'utf8'
    );
    
    process.exit(1);
  }
}

// 스크립트 실행
if (require.main === module) {
  syncNotionData();
}

module.exports = { syncNotionData, fetchAllAssets, calculateStatistics };
