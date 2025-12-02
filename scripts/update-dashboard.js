#!/usr/bin/env node
/**
 * 아산시 스마트시티 자산관리 시스템 - 대시보드 업데이트
 * 
 * 동기화된 JSON 데이터를 바탕으로 대시보드 HTML을 업데이트합니다.
 * 
 * @author Danny (제일엔지니어링 PMO)
 * @version 4.0.0
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const ROOT_DIR = path.join(__dirname, '..');

/**
 * JSON 파일 로드
 */
function loadJsonFile(filename) {
  const filepath = path.join(DATA_DIR, filename);
  if (fs.existsSync(filepath)) {
    return JSON.parse(fs.readFileSync(filepath, 'utf8'));
  }
  return null;
}

/**
 * 숫자 포맷팅 (억원 단위)
 */
function formatCurrency(value) {
  if (value >= 100000000) {
    return `${(value / 100000000).toFixed(1)}억`;
  } else if (value >= 10000) {
    return `${(value / 10000).toFixed(0)}만`;
  }
  return value.toLocaleString();
}

/**
 * 대시보드 데이터 통합
 */
function prepareDashboardData() {
  const assets = loadJsonFile('assets.json') || [];
  const statistics = loadJsonFile('statistics.json') || {};
  const infraProjects = loadJsonFile('infra-projects.json') || [];
  const upcomingAssets = loadJsonFile('upcoming-assets.json') || [];
  const risks = loadJsonFile('risks.json') || [];
  const budget = loadJsonFile('budget.json') || {};
  const syncInfo = loadJsonFile('sync-info.json') || {};
  
  // D-Day 계산 (2025년 12월 31일 기준)
  const endDate = new Date('2025-12-31');
  const today = new Date();
  const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
  
  // 대시보드용 데이터 구성
  const dashboardData = {
    // 메타 정보
    lastSync: syncInfo.lastSyncKST || new Date().toLocaleString('ko-KR'),
    syncStatus: syncInfo.status || 'unknown',
    
    // KPI 데이터
    kpi: {
      totalAssets: statistics.totalAssets || assets.length,
      totalValue: statistics.totalValue || 0,
      totalValueFormatted: formatCurrency(statistics.totalValue || 0),
      operationRate: 100, // 가동률
      executionRate: budget.executionRate || 0,
      warrantyActiveRate: statistics.totalAssets > 0 
        ? Math.round((statistics.warrantyActive / statistics.totalAssets) * 100) 
        : 0,
      daysRemaining: daysRemaining > 0 ? daysRemaining : 0,
    },
    
    // 카테고리별 데이터 (차트용)
    categoryChart: Object.entries(statistics.byCategory || {}).map(([name, data]) => ({
      name,
      count: data.count,
      value: data.value,
    })),
    
    // 담당자별 데이터 (차트용)
    managerChart: Object.entries(statistics.byManager || {}).map(([name, data]) => ({
      name,
      count: data.count,
    })),
    
    // 최근 자산 (테이블용)
    recentAssets: assets
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
      .slice(0, 10)
      .map(a => ({
        name: a.name || '-',
        category: a.category || '-',
        status: a.status || '-',
        value: formatCurrency(a.totalValue || a.unitPrice || 0),
        manager: a.manager || '-',
        date: a.createdAt ? new Date(a.createdAt).toLocaleDateString('ko-KR') : '-',
      })),
    
    // 인프라 프로젝트
    infraProjects: infraProjects.map(p => ({
      ...p,
      budgetFormatted: formatCurrency(p.budget),
    })),
    
    // 도입 예정 자산
    upcomingAssets: upcomingAssets.map(a => ({
      ...a,
      valueFormatted: formatCurrency(a.value || 0),
      expectedDateFormatted: a.expectedDate 
        ? new Date(a.expectedDate).toLocaleDateString('ko-KR') 
        : '-',
    })),
    
    // 리스크
    risks: risks.slice(0, 10),
    
    // 예산
    budget: {
      ...budget,
      totalFormatted: formatCurrency(budget.total || 0),
      executedFormatted: formatCurrency(budget.executed || 0),
      remainingFormatted: formatCurrency(budget.remaining || 0),
    },
  };
  
  return dashboardData;
}

/**
 * dashboard-data.json 생성
 */
function updateDashboard() {
  console.log('🔄 대시보드 데이터 업데이트 시작...');
  
  const dashboardData = prepareDashboardData();
  
  // dashboard-data.json 저장
  const outputPath = path.join(DATA_DIR, 'dashboard-data.json');
  fs.writeFileSync(outputPath, JSON.stringify(dashboardData, null, 2), 'utf8');
  console.log(`✅ ${outputPath} 저장 완료`);
  
  // 요약 출력
  console.log('───────────────────────────────────────────────────────────────');
  console.log('📊 대시보드 데이터 요약:');
  console.log(`   • 총 자산: ${dashboardData.kpi.totalAssets}개`);
  console.log(`   • 총 가치: ₩${dashboardData.kpi.totalValueFormatted}`);
  console.log(`   • 예산 집행률: ${dashboardData.kpi.executionRate}%`);
  console.log(`   • 남은 기간: ${dashboardData.kpi.daysRemaining}일`);
  console.log(`   • 카테고리: ${dashboardData.categoryChart.length}개`);
  console.log(`   • 리스크: ${dashboardData.risks.length}건`);
  console.log('───────────────────────────────────────────────────────────────');
  
  return dashboardData;
}

// 실행
if (require.main === module) {
  updateDashboard();
}

module.exports = { updateDashboard, prepareDashboardData };
