const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function captureJRPG() {
  console.log('🚀 Starting JRPG screenshot automation...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  // Set window size
  await page.setViewport({ width: 1000, height: 900 });
  
  // Load local link.html file
  const fileUrl = 'file://' + path.resolve(__dirname, '../link.html');
  console.log(`🔗 Loading: ${fileUrl}`);
  await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 });
  
  // Wait for initial load
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // 1. Click "太空戰士模式" Tab (tabBtnTeamRaid)
  console.log('🖱️ Clicking tabBtnTeamRaid...');
  await page.click('#tabBtnTeamRaid');
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Take screenshot of Stage Select Grid
  const selectGridPath = path.resolve(__dirname, 'jrpg_1_stage_select.png');
  await page.screenshot({ path: selectGridPath });
  console.log(`📸 Saved Stage Select to: ${selectGridPath}`);
  
  // 2. Click Stage 1 to start battle
  console.log('⚔️ Starting Stage 1 Battle...');
  const stageCards = await page.$$('#teamRaidStageSelectGrid .team-raid-stage-card');
  if (stageCards && stageCards.length > 0) {
    await stageCards[0].click();
    await new Promise(resolve => setTimeout(resolve, 800)); // wait for battle load
    
    // Take screenshot of active battle stage
    const battleStagePath = path.resolve(__dirname, 'jrpg_2_battle_stage.png');
    await page.screenshot({ path: battleStagePath });
    console.log(`📸 Saved Battle Stage to: ${battleStagePath}`);
  } else {
    console.log('⚠️ Stage cards not found!');
  }
  
  // 3. Trigger Fake Victory Book Hook for Stage 3 (Zone 1 Boss)
  console.log('🏆 Triggering Zone 1 BOSS Victory (Stage 3)...');
  await page.evaluate(() => {
    if (typeof window.showTeamRaidVictoryOverlay === 'function') {
      window.showTeamRaidVictoryOverlay(3, 160);
    }
  });
  await new Promise(resolve => setTimeout(resolve, 500));
  const bossVictory3Path = path.resolve(__dirname, 'jrpg_3_boss_victory_zone1.png');
  await page.screenshot({ path: bossVictory3Path });
  console.log(`📸 Saved Zone 1 Boss Victory to: ${bossVictory3Path}`);
  
  // 4. Trigger Fake Victory Book Hook for Stage 6 (Zone 2 Boss)
  console.log('🏆 Triggering Zone 2 BOSS Victory (Stage 6)...');
  await page.evaluate(() => {
    if (typeof window.showTeamRaidVictoryOverlay === 'function') {
      window.showTeamRaidVictoryOverlay(6, 400);
    }
  });
  await new Promise(resolve => setTimeout(resolve, 500));
  const bossVictory6Path = path.resolve(__dirname, 'jrpg_4_boss_victory_zone2.png');
  await page.screenshot({ path: bossVictory6Path });
  console.log(`📸 Saved Zone 2 Boss Victory to: ${bossVictory6Path}`);

  // 5. Trigger Fake Victory Book Hook for Stage 10 (Zone 3 Boss)
  console.log('🏆 Triggering Zone 3 BOSS Victory (Stage 10)...');
  await page.evaluate(() => {
    if (typeof window.showTeamRaidVictoryOverlay === 'function') {
      window.showTeamRaidVictoryOverlay(10, 1000);
    }
  });
  await new Promise(resolve => setTimeout(resolve, 500));
  const bossVictory10Path = path.resolve(__dirname, 'jrpg_5_boss_victory_zone3.png');
  await page.screenshot({ path: bossVictory10Path });
  console.log(`📸 Saved Zone 3 Boss Victory to: ${bossVictory10Path}`);

  // 6. Trigger Defeat Overlay
  console.log('💀 Triggering Defeat Overlay...');
  await page.evaluate(() => {
    if (typeof window.showTeamRaidDefeatOverlay === 'function') {
      window.showTeamRaidDefeatOverlay();
    }
  });
  await new Promise(resolve => setTimeout(resolve, 500));
  const defeatPath = path.resolve(__dirname, 'jrpg_6_defeat.png');
  await page.screenshot({ path: defeatPath });
  console.log(`📸 Saved Defeat Overlay to: ${defeatPath}`);
  
  await browser.close();
  console.log('🎯 JRPG screenshot automation completed successfully!');
}

captureJRPG().catch(err => {
  console.error('❌ Error during JRPG capture:', err);
  process.exit(1);
});
