/**
 * ⚔️ 《白熊人生戰役：太空戰士模式》獨立 JRPG 團隊戰鬥引擎
 * 職責：管理戰鬥狀態、成員與魔物屬性、ATB 時間軸充能、指令執行與角色定位調換
 */

class rpgCharacter {
  constructor(name, type, emoji, attrType, baseHp, baseMp, speed, power, img) {
    this.name = name;
    this.type = type; // 'bear' (Sage), 'cat' (Warrior), 'rabbit' (White Mage), 'monkey' (Ninja)
    this.emoji = emoji;
    this.attrType = attrType; // 'int', 'vit', 'foc', 'agi'
    this.baseHp = baseHp;
    this.baseMp = baseMp;
    this.speed = speed; // 敏捷，決定 ATB 充能速度
    this.power = power; // 基礎法術/物理攻擊力
    this.img = img || `assets/hero_${type}.png`; // 載入自定義像素角色圖片
    
    // 即時戰鬥數值
    this.hp = baseHp;
    this.maxHp = baseHp;
    this.mp = baseMp;
    this.maxMp = baseMp;
    this.atb = 0; // ATB 行動值 (0 - 100)
    
    // 狀態
    this.alive = true;
    this.isShielded = false; // 降噪防護罩 (減傷 50%)
    this.isTaunting = false; // 戰士嘲諷
  }

  reset() {
    this.hp = this.maxHp;
    this.mp = this.maxMp;
    this.atb = 0;
    this.alive = true;
    this.isShielded = false;
    this.isTaunting = false;
  }
}

class rpgMonster {
  constructor(name, emoji, stage, img) {
    this.name = name;
    this.emoji = emoji;
    this.img = img || "assets/monster_slime.png"; // 載入高清怪物圖片
    
    // 關卡指數倍數增長機制
    const hpMultiplier = Math.pow(1.50, stage - 1);
    const atkMultiplier = Math.pow(1.45, stage - 1);
    
    this.maxHp = Math.floor(80 * hpMultiplier);
    this.hp = this.maxHp;
    this.atk = Math.floor(10 * atkMultiplier);
    this.speed = Math.floor(25 + stage * 0.8); // 怪物速度隨關卡微增
    
    this.atb = 0;
    this.alive = true;
    this.isShocked = false; // 被賢者白熊感電 (受傷 +15%)
    this.shockedTurns = 0;
    
    // 擊敗獎勵 (正比經驗值)
    this.xpReward = Math.floor(50 * Math.pow(1.6, stage - 1));
  }
}

class rpgBattleEngine {
  constructor(options = {}) {
    this.stage = 1;
    this.heroes = [];
    this.monsters = [];
    this.isBattleActive = false;
    this.isPaused = false; // ATB 充能暫停中 (等待指令或動畫播放)
    this.battleLog = [];
    
    // 註冊回呼函數以更新 UI
    this.onLog = options.onLog || (() => {});
    this.onStateChange = options.onStateChange || (() => {});
    this.onActionPrompt = options.onActionPrompt || (() => {}); // 英雄 ATB 滿時觸發選單
    this.onAnimation = options.onAnimation || (() => {}); // 攻擊特效播放
    this.onVictory = options.onVictory || (() => {});
    this.onDefeat = options.onDefeat || (() => {});
  }

  // 初始化小隊與等級連動
  initParty(userLevel, gearStats = {}) {
    this.heroes = [];
    
    // 1. 🔮 賢者 ➔【白熊】 (Sage) - 核心，始終解鎖
    const bearHp = 120 + (gearStats.bonusMaxHp || 0);
    const bearInt = 20 + (gearStats.bonusInt || 0);
    const bearAgi = 25 + (gearStats.bonusAgi || 0);
    this.heroes.push(new rpgCharacter("白熊", "bear", "🐻‍❄️", "int", bearHp, 100, bearAgi, bearInt, "assets/hero_bear_sage.png"));

    // 2. 🪓 戰士 ➔【除錯小貓】 (Warrior) - 核心，始終解鎖 (把怪物當 Bug 除錯的勇猛前排)
    const catHp = 160 + (gearStats.bonusMaxHp || 0); // 戰士血量高
    const catVit = 18 + (gearStats.bonusVit || 0);
    const catAgi = 22 + (gearStats.bonusAgi || 0); // 前排中速
    this.heroes.push(new rpgCharacter("除錯小貓", "cat", "🐱", "vit", catHp, 60, catAgi, catVit, "assets/hero_cat_warrior.png"));

    // 3. 🤍 白魔導士 ➔【降噪小兔】 (White Mage) - LV.5 解鎖 (心靈降噪治療擔當)
    if (userLevel >= 5) {
      const rabbitHp = 100 + (gearStats.bonusMaxHp || 0);
      const rabbitFoc = 15 + (gearStats.bonusFoc || 0);
      const rabbitAgi = 28 + (gearStats.bonusAgi || 0); // 白魔導士高速補血
      this.heroes.push(new rpgCharacter("降噪小兔", "rabbit", "🐰", "foc", rabbitHp, 120, rabbitAgi, rabbitFoc, "assets/hero_rabbit_mage.png"));
    }

    // 4. 🗡️ 忍者 ➔【理智小猴】 (Ninja) - LV.15 解鎖 (超敏捷執行力爆發)
    if (userLevel >= 15) {
      const monkeyHp = 90 + (gearStats.bonusMaxHp || 0);
      const monkeyAgi = 40 + (gearStats.bonusAgi || 0); // 忍者超高速
      this.heroes.push(new rpgCharacter("理智小猴", "monkey", "🐵", "agi", monkeyHp, 80, monkeyAgi, monkeyAgi, "assets/hero_monkey_ninja.png"));
    }
  }

  // 開始新關卡戰鬥
  startBattle(stage) {
    this.stage = stage;
    this.isBattleActive = true;
    this.isPaused = false;
    this.battleLog = [];
    
    // 重置英雄數值
    this.heroes.forEach(h => h.reset());
    
    // 依據關卡生成 1 - 3 隻模物
    this.monsters = [];
    const monsterPool = [
      { name: "雜念史萊姆", emoji: "👾", img: "assets/monster_slime.png" },
      { name: "分心大眼怪", emoji: "👁️", img: "assets/monster_eye.png" },
      { name: "干擾噪音獸", emoji: "🔊", img: "assets/monster_noise.png" },
      { name: "阻力石金人", emoji: "🧱", img: "assets/monster_golem.png" },
      { name: "硬殼酸蝸牛", emoji: "🐌", img: "assets/monster_snail.png" },
      { name: "心靈魔巫師", emoji: "🧙", img: "assets/monster_wizard.png" },
      { name: "暗黑魔騎士", emoji: "🛡️", img: "assets/monster_knight.png" },
      { name: "撕裂怨靈魂", emoji: "👻", img: "assets/monster_ghost.png" },
      { name: "命運大死神", emoji: "💀", img: "assets/monster_reaper.png" },
      { name: "深淵防衛龍", emoji: "🐉", img: "assets/monster_dragon.png" }
    ];
    
    let count = 1;
    if (stage >= 3) count = 2;
    if (stage >= 8) count = 3;
    
    for (let i = 0; i < count; i++) {
      const poolIdx = (stage - 1 + i) % monsterPool.length;
      const template = monsterPool[poolIdx];
      const name = `關卡 ${stage} 魔物・${template.name}`;
      this.monsters.push(new rpgMonster(name, template.emoji, stage, template.img));
    }
    
    this.log(`⚔️ 團隊副本第 ${stage} 關戰役正式拉開帷幕！敵人已出現在前線！`);
    this.onStateChange();
  }

  // ATB 時間軸時鐘更新 (每幀調用)
  updateATB(dt = 0.5) {
    if (!this.isBattleActive || this.isPaused) return;

    // 1. 英雄 ATB 充能
    for (let hero of this.heroes) {
      if (!hero.alive) continue;
      hero.atb += hero.speed * dt * 0.15;
      if (hero.atb >= 100) {
        hero.atb = 100;
        this.isPaused = true; // 暫停充能，等待指令
        this.onActionPrompt(hero);
        this.onStateChange();
        return;
      }
    }

    // 2. 怪物 ATB 充能
    for (let monster of this.monsters) {
      if (!monster.alive) continue;
      monster.atb += monster.speed * dt * 0.15;
      if (monster.atb >= 100) {
        monster.atb = 0; // 怪物充能完畢直接發起攻擊，不暫停
        this.monsterAction(monster);
        this.onStateChange();
        return;
      }
    }

    this.onStateChange();
  }

  // 怪物發起攻擊
  monsterAction(monster) {
    if (!this.isBattleActive || !monster.alive) return;
    
    // 結算怪物身上的感電狀態回合
    if (monster.isShocked) {
      monster.shockedTurns--;
      if (monster.shockedTurns <= 0) {
        monster.isShocked = false;
        this.log(`✨ ${monster.emoji}${monster.name} 的感電負面狀態已消失。`);
      }
    }

    // 選擇攻擊目標：優先選擇戰士嘲諷者，否則隨機選擇存活的英雄
    let target = null;
    const activeHeroes = this.heroes.filter(h => h.alive);
    if (activeHeroes.length === 0) return;

    const tauntingHero = activeHeroes.find(h => h.isTaunting);
    if (tauntingHero) {
      target = tauntingHero;
    } else {
      const idx = Math.floor(Math.random() * activeHeroes.length);
      target = activeHeroes[idx];
    }

    // 暫時阻斷充能，開始怪獸的攻擊動畫
    this.isPaused = true;
    
    // 計算傷害與防禦 (白魔導士護盾減傷 50%)
    let dmg = Math.floor(monster.atk * (0.85 + Math.random() * 0.3));
    if (target.isShielded) {
      dmg = Math.floor(dmg * 0.5);
      target.isShielded = false; // 護盾抵擋一次後消失
      this.log(`🛡️ ${target.emoji}【${target.name}】使用【降噪防護罩】抵擋，傷害折半！`);
    }

    this.onAnimation('monster-attack', { attacker: monster, target: target });

    setTimeout(() => {
      target.hp -= dmg;
      if (target.hp <= 0) {
        target.hp = 0;
        target.alive = false;
        target.atb = 0;
        target.isTaunting = false;
        this.log(`💀 🔴 隊員 ${target.emoji}【${target.name}】生命值耗盡倒下了！`);
      } else {
        this.log(`💥 ${monster.emoji}${monster.name} 使出重擊！對 ${target.emoji}【${target.name}】造成 ${dmg} 點物理傷害！`);
      }

      // 如果嘲諷者受擊，嘲諷效果消失
      if (target.isTaunting) {
        target.isTaunting = false;
      }

      this.checkBattleStatus();
      this.isPaused = false;
      this.onStateChange();
    }, 600);
  }

  // 英雄執行特技/魔法
  executeHeroSkill(hero, skillType, targetMonsterIdx) {
    if (!this.isBattleActive || !hero.alive) return;
    
    const target = this.monsters[targetMonsterIdx];
    if (!target || !target.alive) {
      // 若目標死亡，自動尋找第一個存活的魔物
      const firstAlive = this.monsters.find(m => m.alive);
      if (!firstAlive) return;
    }
    
    const realTarget = target && target.alive ? target : this.monsters.find(m => m.alive);
    this.isPaused = true;

    // --- 🔮 1. 賢者白熊 ➔ ⚡閃煉雷擊 (Sage: Lightning Storm) ---
    if (hero.type === 'bear') {
      if (hero.mp < 20) {
        this.log(`❌ 🔮 賢者【白熊】MP 不足，無法釋放【閃煉雷擊】！`);
        this.isPaused = false;
        return;
      }
      hero.mp -= 20;
      this.log(`🔮 ⚡ 賢者【白熊】高舉長杖，念動複利神咒釋放【全體・閃煉雷擊】！`);
      
      this.onAnimation('lightning', { attacker: hero, targets: this.monsters.filter(m => m.alive) });

      setTimeout(() => {
        this.monsters.forEach(m => {
          if (m.alive) {
            let dmg = Math.floor(hero.power * 1.5 * (0.9 + Math.random() * 0.2));
            m.hp -= dmg;
            m.isShocked = true;
            m.shockedTurns = 2; // 感電 2 回合
            this.log(`⚡ 雷霆轟頂！對 ${m.emoji}${m.name} 造成了 ${dmg} 點雷電法術傷害，並使其「感電受傷 +15%」（持續 2 回合）！`);
            if (m.hp <= 0) {
              m.hp = 0;
              m.alive = false;
              m.atb = 0;
              this.log(`💀 🟢 敵方 ${m.emoji}${m.name} 被雷霆徹底淨化擊敗！`);
            }
          }
        });
        hero.atb = 0;
        this.checkBattleStatus();
        this.isPaused = false;
        this.onStateChange();
      }, 700);
    }

    // --- 🗡️ 2. 忍者理智小猴 ➔ ⚔️執行斬 (Ninja: Blade Flurry) ---
    else if (hero.type === 'monkey') {
      if (hero.mp < 15) {
        this.log(`❌ 🗡️ 忍者【理智小猴】MP 不足，無法釋放【執行斬】！`);
        this.isPaused = false;
        return;
      }
      hero.mp -= 15;
      this.log(`🗡️ 🐵 忍者【理智小猴】化身一道疾風黑影，突進至敵陣使出【執行斬】！`);
      
      this.onAnimation('slash-monkey', { attacker: hero, target: realTarget });

      setTimeout(() => {
        // 高速 3 連斬
        let logs = [];
        let totalDmg = 0;
        for (let i = 0; i < 3; i++) {
          let hit = Math.floor(hero.power * 0.5 * (0.8 + Math.random() * 0.4));
          if (realTarget.isShocked) {
            hit = Math.floor(hit * 1.15); // 感電額外受傷 15%
          }
          totalDmg += hit;
        }

        // 25% 機率觸發影子雙重斬擊
        if (Math.random() < 0.25) {
          const shadowDmg = Math.floor(hero.power * 0.6);
          totalDmg += shadowDmg;
          this.log(`👥 ✨ 觸發影子殘像！額外追加了 ${shadowDmg} 點影子連擊傷害！`);
        }

        realTarget.hp -= totalDmg;
        this.log(`⚔️ 🐵【理智小猴】發動連續幻影斬擊！對 ${realTarget.emoji}${realTarget.name} 造成了 ${totalDmg} 點物理爆發傷害！`);
        
        if (realTarget.hp <= 0) {
          realTarget.hp = 0;
          realTarget.alive = false;
          realTarget.atb = 0;
          this.log(`💀 🟢 敵方 ${realTarget.emoji}${realTarget.name} 被理智小猴的執行斬大卸八塊！`);
        }

        hero.atb = 0;
        this.checkBattleStatus();
        this.isPaused = false;
        this.onStateChange();
      }, 600);
    }

    // --- 🪓 3. 戰士除錯小貓 ➔ ⚡除錯專注擊 (Warrior: Debug Slash) ---
    else if (hero.type === 'cat') {
      if (hero.mp < 18) {
        this.log(`❌ 🪓 戰士【除錯小貓】MP 不足，無法釋放【除錯專注擊】！`);
        this.isPaused = false;
        return;
      }
      hero.mp -= 18;
      this.log(`🪓 🐱 戰士【除錯小貓】全身爆發除錯代碼氣流，扛起巨刃悍不畏死發動【除錯專注擊】！`);
      
      this.onAnimation('slash-cat', { attacker: hero, target: realTarget });

      setTimeout(() => {
        // 心靈破防真實傷害 (無視防禦)
        let dmg = Math.floor(hero.power * 1.4 * (0.95 + Math.random() * 0.1));
        if (realTarget.isShocked) {
          dmg = Math.floor(dmg * 1.15); // 感電加成
        }
        
        realTarget.hp -= dmg;
        hero.isTaunting = true; // 嘲諷敵人，使怪獸下一擊必打小貓
        
        this.log(`🛡️ 代碼精準破防！🐱【除錯小貓】一擊除錯！對 ${realTarget.emoji}${realTarget.name} 造成了 ${dmg} 點【無視防禦真實傷害】，並強行嘲諷魔物！`);
        
        if (realTarget.hp <= 0) {
          realTarget.hp = 0;
          realTarget.alive = false;
          realTarget.atb = 0;
          this.log(`💀 🟢 敵方 ${realTarget.emoji}${realTarget.name} 承受不住小貓的除錯重擊而崩潰！`);
        }

        hero.atb = 0;
        this.checkBattleStatus();
        this.isPaused = false;
        this.onStateChange();
      }, 600);
    }

    // --- 🤍 4. 白魔導士降噪小兔 ➔ 🛡️降噪防護罩 (White Mage: Noise Shelter) ---
    else if (hero.type === 'rabbit') {
      if (hero.mp < 25) {
        this.log(`❌ 🤍 白魔導士【降噪小兔】MP 不足，無法釋放【降噪防護罩】！`);
        this.isPaused = false;
        return;
      }
      hero.mp -= 25;
      this.log(`🤍 🐰 白魔導士【降噪小兔】念動防護咒文，為全隊建立【全體・降噪防護罩】！`);
      
      this.onAnimation('heal-shield', { attacker: hero, targets: this.heroes.filter(h => h.alive) });

      setTimeout(() => {
        // 全體治療
        this.heroes.forEach(h => {
          if (h.alive) {
            const heal = Math.floor(hero.power * 1.2 * (0.9 + Math.random() * 0.2));
            h.hp += heal;
            if (h.hp > h.maxHp) h.hp = h.maxHp;
            h.isShielded = true; // 進入減傷狀態
            this.log(`💚 🐰【降噪小兔】的降噪療癒力場溫暖浮現！【${h.name}】回復了 ${heal} 點 HP，並被降噪光膜所庇護（下一次受傷減半）！`);
          }
        });
        hero.atb = 0;
        this.isPaused = false;
        this.onStateChange();
      }, 600);
    }
  }

  // 英雄執行普通攻擊 (不耗 MP)
  executeHeroAttack(hero, targetMonsterIdx) {
    if (!this.isBattleActive || !hero.alive) return;
    
    const target = this.monsters[targetMonsterIdx];
    const realTarget = target && target.alive ? target : this.monsters.find(m => m.alive);
    if (!realTarget) return;

    this.isPaused = true;
    this.log(`⚔️ ${hero.emoji}【${hero.name}】舉起武器對 ${realTarget.emoji}${realTarget.name} 發起普通物理攻擊！`);
    
    this.onAnimation('normal-attack', { attacker: hero, target: realTarget });

    setTimeout(() => {
      let dmg = Math.floor(hero.power * 0.8 * (0.85 + Math.random() * 0.3));
      if (realTarget.isShocked) {
        dmg = Math.floor(dmg * 1.15); // 感電傷害 +15%
      }
      realTarget.hp -= dmg;
      this.log(`💥 命中了！造成了 ${dmg} 點傷害！`);
      
      if (realTarget.hp <= 0) {
        realTarget.hp = 0;
        realTarget.alive = false;
        realTarget.atb = 0;
        this.log(`💀 🟢 敵方 ${realTarget.emoji}${realTarget.name} 倒下了！`);
      }

      hero.atb = 0;
      this.checkBattleStatus();
      this.isPaused = false;
      this.onStateChange();
    }, 500);
  }

  // 檢查戰鬥是否結束
  checkBattleStatus() {
    // 1. 檢查魔物是否全滅
    const aliveMonsters = this.monsters.filter(m => m.alive);
    if (aliveMonsters.length === 0) {
      this.isBattleActive = false;
      
      // 累加獲取的所有經驗值
      let totalXp = 0;
      this.monsters.forEach(m => totalXp += m.xpReward);
      
      this.log(`🎉 🟢 勝利！隊友合力剿滅了所有深淵魔物！共收穫了 +${totalXp} 經驗值 (XP)！`);
      this.onVictory(totalXp);
      return;
    }

    // 2. 檢查小隊是否全滅
    const aliveHeroes = this.heroes.filter(h => h.alive);
    if (aliveHeroes.length === 0) {
      this.isBattleActive = false;
      this.log(`💀 🔴 戰敗！全員均被魔物擊倒，本次冒險鎩羽而歸。回去修煉更高等級解鎖隊友吧！`);
      this.onDefeat();
      return;
    }
  }

  log(msg) {
    this.battleLog.unshift(msg); // 新日誌插到最前
    if (this.battleLog.length > 50) this.battleLog.pop();
    this.onLog(msg);
  }
}

// 導出到全域，以便在 link.html 中直接 new
window.rpgBattleEngine = rpgBattleEngine;
