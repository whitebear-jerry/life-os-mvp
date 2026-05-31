const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function capture(suffix) {
  console.log(`Starting capture for: ${suffix}`);
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  // Local link.html file URL
  const fileUrl = 'file:///Users/whitebebear/Desktop/life-os-mvp/life-os-mvp/link.html';
  console.log(`Loading URL: ${fileUrl}`);
  
  // 1. Capture Desktop (520px max width shell, viewport 1200x800)
  await page.setViewport({ width: 1200, height: 1600 });
  await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 });
  
  // 自動點開團隊副本並開始第一關卡戰鬥 (用來生成最具震撼力的實測戰鬥畫面)
  await page.evaluate(() => {
    if (typeof switchGuildTab === 'function') {
      switchGuildTab('teamRaid');
      if (typeof startTeamRaidBattle === 'function') {
        startTeamRaidBattle(1, 1, {});
      }
    }
  });

  // 等待戰鬥初始化與精靈定位渲染完成
  await new Promise(resolve => setTimeout(resolve, 1200));
  
  const destDir = '/Users/whitebebear/.gemini/antigravity/brain/8b56a159-5108-4085-994e-b58a1e305a24'; 
  const desktopPath = path.join(destDir, `link_desktop_${suffix}.png`);
  await page.screenshot({ path: desktopPath, fullPage: false });
  console.log(`Saved desktop to: ${desktopPath}`);
  
  // 2. Capture Mobile (375px width, viewport 375x812)
  await page.setViewport({ width: 375, height: 1500 });
  // Reload or resize
  await new Promise(resolve => setTimeout(resolve, 300));
  
  const mobilePath = path.join(destDir, `link_mobile_${suffix}.png`);
  await page.screenshot({ path: mobilePath, fullPage: false });
  console.log(`Saved mobile to: ${mobilePath}`);
  
  await browser.close();
  console.log('Capture finished successfully!');
}

const mode = process.argv[2] || 'before';
capture(mode).catch(err => {
  console.error('Error during capture:', err);
  process.exit(1);
});
