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
  constructor(name, emoji, stage, img, isBoss = false) {
    this.name = name;
    this.emoji = emoji;
    this.img = img || "assets/monster_slime.png"; // 載入高清怪物圖片
    this.isBoss = isBoss;
    
    // 關卡指數倍數增長機制 (基礎血量改為 2000，完美對齊玩家 7000+ HP)
    let hpMultiplier = Math.pow(1.35, stage - 1);
    let atkMultiplier = Math.pow(1.30, stage - 1);
    
    if (isBoss) {
      hpMultiplier *= 2.0; // Boss 血量翻倍
      atkMultiplier *= 1.25; // Boss 傷害提升 25%
    }
    
    this.maxHp = Math.floor(2000 * hpMultiplier);
    this.hp = this.maxHp;
    this.atk = Math.floor(65 * atkMultiplier); // 調整基礎攻擊力，避免秒殺，形成持久戰！
    this.speed = Math.floor(25 + stage * 0.8 + (isBoss ? 5 : 0)); // Boss 速度微增
    
    this.atb = 0;
    this.alive = true;
    this.isShocked = false; // 被賢者白熊感電 (受傷 +15%)
    this.shockedTurns = 0;
    
    // 擊敗獎勵 (正比經驗值，Boss 額外加成)
    this.xpReward = Math.floor(50 * Math.pow(1.6, stage - 1) * (isBoss ? 2.5 : 1));
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

  // 初始化小隊與等級連動 (100% 承襲修煉等級、四維屬性與神裝加成，展現與文字大冒險完全對齊的強悍屬性)
  initParty(userLevel, gearStats = {}, userAttrs = { int: 10, vit: 10, foc: 10, agi: 10 }) {
    this.heroes = [];
    
    // 確保 userAttrs 具有基礎默認值，避免未定義錯誤
    const attrs = {
      int: userAttrs.int || 10,
      vit: userAttrs.vit || 10,
      foc: userAttrs.foc || 10,
      agi: userAttrs.agi || 10
    };
    
    // 1. 🔮 賢者 ➔【白熊】 (Sage) - 智慧 (INT) 連動
    let bearHp = 60 + userLevel * 3 + (attrs.int + (gearStats.bonusInt || 0)) * 8 + (gearStats.bonusMaxHp || 0);
    const bearInt = 20 + userLevel * 0.5 + (attrs.int + (gearStats.bonusInt || 0)) * 1.5;
    const bearAgi = 25 + userLevel * 0.2 + (attrs.agi + (gearStats.bonusAgi || 0)) * 0.5;

    // 2. 🪓 戰士 ➔【除錯小貓】 (Warrior) - 韌性 (VIT) 連動 (血量最高，前排坦怪)
    let catHp = 60 + userLevel * 3 + (attrs.vit + (gearStats.bonusVit || 0)) * 10 + (gearStats.bonusMaxHp || 0);
    const catVit = 18 + userLevel * 0.4 + (attrs.vit + (gearStats.bonusVit || 0)) * 1.8;
    const catAgi = 22 + userLevel * 0.2 + (attrs.agi + (gearStats.bonusAgi || 0)) * 0.4;

    // 3. 🤍 白魔導士 ➔【降噪小兔】 (White Mage) - 專注 (FOC) 連動 (LV.5 解鎖)
    let rabbitHp = 100;
    let rabbitFoc = 15 + userLevel * 0.3 + (attrs.foc + (gearStats.bonusFoc || 0)) * 1.6;
    let rabbitAgi = 28 + userLevel * 0.25 + (attrs.agi + (gearStats.bonusAgi || 0)) * 0.6;
    if (userLevel >= 5) {
      rabbitHp = 60 + userLevel * 3 + (attrs.foc + (gearStats.bonusFoc || 0)) * 8 + (gearStats.bonusMaxHp || 0);
    }

    // 4. 🗡️ 忍者 ➔【能量小猴】 (Ninja) - 綜合戰力與通用輔助，通用物理複數攻擊 (LV.15 解鎖)
    let monkeyHp = 90;
    let monkeyAgi = 40 + userLevel * 0.6 + (attrs.agi + (gearStats.bonusAgi || 0)) * 2.0;
    if (userLevel >= 15) {
      monkeyHp = 60 + userLevel * 3 + (attrs.agi + (gearStats.bonusAgi || 0)) * 8 + (gearStats.bonusMaxHp || 0);
    }

    // 🌟 100% 零誤差絕對承襲日常文字冒險 JRPG 全隊生命值！如果全域 party 存在就直接載入！
    if (typeof window !== 'undefined' && window.party && window.party.length >= 4) {
      bearHp = window.party[0].maxHp || bearHp;
      catHp = window.party[1].maxHp || catHp;
      rabbitHp = window.party[2].maxHp || rabbitHp;
      monkeyHp = window.party[3].maxHp || monkeyHp;
      console.log("JRPG successfully inherited stats from window.party:", bearHp, catHp, rabbitHp, monkeyHp);
    }

    this.heroes.push(new rpgCharacter("白熊", "bear", "🐻‍❄️", "int", bearHp, 100, bearAgi, bearInt, "assets/hero_bear_sage.png"));
    this.heroes.push(new rpgCharacter("除錯小貓", "cat", "🐱", "vit", catHp, 60, catAgi, catVit, "assets/hero_cat_warrior.png"));
    if (userLevel >= 5) {
      this.heroes.push(new rpgCharacter("降噪小兔", "rabbit", "🐰", "foc", rabbitHp, 120, rabbitAgi, rabbitFoc, "assets/hero_rabbit_mage.png"));
    }
    if (userLevel >= 15) {
      this.heroes.push(new rpgCharacter("能量小猴", "monkey", "🐵", "agi", monkeyHp, 80, monkeyAgi, monkeyAgi, "assets/hero_monkey_ninja.png"));
    }
  }

  // 開始新關卡戰鬥 (對應三大書本 Zone 的關卡體系，怪物難度與血量全面平衡)
  startBattle(stage) {
    this.stage = stage;
    this.isBattleActive = true;
    this.isPaused = false;
    this.battleLog = [];
    
    // 重置英雄數值
    this.heroes.forEach(h => h.reset());
    
    // 依據關卡生成特定魔物
    this.monsters = [];
    let monstersData = [];

    // --- Zone 1「內耗深淵」 ➔ 對應《降噪人生》 ---
    if (stage === 1) {
      monstersData = [
        { name: "內耗深淵・雜念史萊姆", emoji: "👾", img: "assets/monster_slime.png", isBoss: false }
      ];
    } else if (stage === 2) {
      monstersData = [
        { name: "內耗深淵・雜念史萊姆", emoji: "👾", img: "assets/monster_slime.png", isBoss: false },
        { name: "內耗深淵・焦慮龍", emoji: "🐉", img: "assets/monster_dragon.png", isBoss: false }
      ];
    } else if (stage === 3) {
      monstersData = [
        { name: "內耗深淵・焦慮龍", emoji: "🐉", img: "assets/monster_dragon.png", isBoss: false },
        { name: "內耗深淵・比較心魔 [BOSS]", emoji: "🧙", img: "assets/monster_wizard.png", isBoss: true }
      ];
    } 
    // --- Zone 2「逆境關卡」 ➔ 對應《人生遊戲》 ---
    else if (stage === 4) {
      monstersData = [
        { name: "逆境關卡・卡關魔", emoji: "🧱", img: "assets/monster_golem.png", isBoss: false }
      ];
    } else if (stage === 5) {
      monstersData = [
        { name: "逆境關卡・卡關魔", emoji: "🧱", img: "assets/monster_golem.png", isBoss: false },
        { name: "逆境關卡・拖延獸", emoji: "🐌", img: "assets/monster_snail.png", isBoss: false }
      ];
    } else if (stage === 6) {
      monstersData = [
        { name: "逆境關卡・拖延獸", emoji: "🐌", img: "assets/monster_snail.png", isBoss: false },
        { name: "逆境關卡・情緒勒索怪 [BOSS]", emoji: "🛡️", img: "assets/monster_knight.png", isBoss: true }
      ];
    } 
    // --- Zone 3「複利之路」 ➔ 對應《人生複利》 ---
    else if (stage === 7) {
      monstersData = [
        { name: "複利之路・短視魔", emoji: "👁️", img: "assets/monster_eye.png", isBoss: false }
      ];
    } else if (stage === 8) {
      monstersData = [
        { name: "複利之路・短視魔", emoji: "👁️", img: "assets/monster_eye.png", isBoss: false },
        { name: "複利之路・放棄龍", emoji: "🐉", img: "assets/monster_dragon.png", isBoss: false }
      ];
    } else if (stage === 9) {
      monstersData = [
        { name: "複利之路・放棄龍", emoji: "🐉", img: "assets/monster_dragon.png", isBoss: false },
        { name: "複利之路・原地打轉獸", emoji: "🔊", img: "assets/monster_noise.png", isBoss: false }
      ];
    } else if (stage === 10) {
      monstersData = [
        { name: "複利之路・原地打轉獸", emoji: "🔊", img: "assets/monster_noise.png", isBoss: false },
        { name: "複利之路・終極放棄怨靈 [BOSS]", emoji: "💀", img: "assets/monster_reaper.png", isBoss: true }
      ];
    }

    monstersData.forEach(m => {
      this.monsters.push(new rpgMonster(m.name, m.emoji, stage, m.img, m.isBoss));
    });
    
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

    // --- 🗡️ 2. 忍者能量小猴 ➔ ⚔️執行斬 (Ninja: Blade Flurry) ---
    else if (hero.type === 'monkey') {
      if (hero.mp < 15) {
        this.log(`❌ 🗡️ 忍者【能量小猴】MP 不足，無法釋放【執行斬】！`);
        this.isPaused = false;
        return;
      }
      hero.mp -= 15;
      this.log(`🗡️ 🐵 忍者【能量小猴】化身疾風黑影，發動複數分身連擊【全體・執行隨機斬】！`);
      
      // 動畫播放
      this.onAnimation('slash-monkey', { attacker: hero, target: realTarget });

      setTimeout(() => {
        // 進行 3 次連斬，每次隨機選擇一個存活的怪物 (複數打法！)
        for (let i = 1; i <= 3; i++) {
          const aliveMonsters = this.monsters.filter(m => m.alive);
          if (aliveMonsters.length === 0) break;
          
          const randMonster = aliveMonsters[Math.floor(Math.random() * aliveMonsters.length)];
          let hit = Math.floor(hero.power * 0.7 * (0.8 + Math.random() * 0.4));
          if (randMonster.isShocked) {
            hit = Math.floor(hit * 1.15); // 感電加成
          }
          
          randMonster.hp -= hit;
          this.log(`🗡️ 第 ${i} 擊！🐵 殘像掠過，對 ${randMonster.emoji}${randMonster.name} 造成了 ${hit} 點物理斬擊傷害！`);
          
          if (randMonster.hp <= 0) {
            randMonster.hp = 0;
            randMonster.alive = false;
            randMonster.atb = 0;
            this.log(`💀 🟢 敵方 ${randMonster.emoji}${randMonster.name} 被能量小猴瞬殺斬殺！`);
          }
        }

        // 35% 高機率觸發影子終結擊
        const aliveMonstersEnd = this.monsters.filter(m => m.alive);
        if (aliveMonstersEnd.length > 0 && Math.random() < 0.35) {
          const randMonster = aliveMonstersEnd[Math.floor(Math.random() * aliveMonstersEnd.length)];
          const shadowDmg = Math.floor(hero.power * 0.8);
          randMonster.hp -= shadowDmg;
          this.log(`👥 ✨ 觸發影子殘像終結！額外對 ${randMonster.emoji}${randMonster.name} 追加 ${shadowDmg} 點影子暗殺真實傷害！`);
          if (randMonster.hp <= 0) {
            randMonster.hp = 0;
            randMonster.alive = false;
            randMonster.atb = 0;
            this.log(`💀 🟢 敵方 ${randMonster.emoji}${randMonster.name} 被影子終結擊碎！`);
          }
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
