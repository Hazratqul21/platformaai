/* ================== AI YORDAMCHI — to'liq ekranli bo'lim ==================
 *
 * O'ng tomondagi panel boshqa ish qilayotib savol berish uchun qulay,
 * lekin TOR: jadval, diagramma va profil oynasi u yerga sig'maydi.
 * Bu bo'lim esa AI bilan ishlash uchun asosiy joy — savol berasiz,
 * hisob-kitob so'raysiz, tizimni sozlaysiz.
 *
 * Yon menyudagi alohida bo'lim bo'lishining ikkinchi sababi:
 * foydalanuvchi «AI qayerda, u nima qilyapti?» degan savolga javob
 * topa olishi kerak. Panel yashiringan bo'lsa AI go'yo yo'q.
 */

let AI_SUHBAT = null;      // joriy suhbat id
let AI_BAND = false;
let AI_KALIT = null;       // qaysi bo'lim yordamchisi
let AI_ROYXAT = [];

PAGES.ai = async () => {
  const [holat, faoliyat] = await Promise.all([
    api('/api/agent/holat'),
    api('/api/agent/faoliyat').catch(() => ({ suhbatlar: [], amallar: [] })),
  ]);
  AI_ROYXAT = holat.agentlar || [];
  if (!AI_KALIT && AI_ROYXAT.length) AI_KALIT = AI_ROYXAT[0].kalit;
  window._postRender = aiOrnat;
  window._aiFaoliyat = faoliyat;

  const tayyor = holat.tayyor;
  return `
  <div class="ai-sahifa">
    <div class="glass card ai-chat-quti">
      <div class="between ai-bosh">
        <div style="min-width:0">
          <select class="fld ai-tanla" id="aiTanla">${AI_ROYXAT
            .map(a => `<option value="${esc(a.kalit)}" ${a.kalit === AI_KALIT ? 'selected' : ''}>${esc(a.nom)}</option>`).join('')}</select>
          <div class="muted ai-holat ${tayyor ? '' : 'ai-ogoh'}" id="aiHolat">
            ${tayyor ? `${esc(holat.provayder)} · ${esc(holat.model)}` : esc(holat.izoh)}
          </div>
        </div>
        <button class="btn sm" onclick="aiYangiSuhbat()">✎ Янги суҳбат</button>
      </div>

      <div class="ai-oqim" id="aiOqim"></div>

      <div id="aiTaklif" class="ai-takliflar"></div>

      <div class="ai-kirish">
        <textarea id="aiMatn" rows="2" ${tayyor ? '' : 'disabled'}
          placeholder="Савол ёзинг ёки буйруқ беринг…"></textarea>
        <button class="btn pri" id="aiYubor" ${tayyor ? '' : 'disabled'}>Юбориш</button>
      </div>
    </div>

    <div class="ai-yon">
      <div class="glass card">
        <h2 class="sec">AI ҳозир нима қиляпти</h2>
        <div class="sec-sub">Ҳар бир ҳаракат шу ерда қолади</div>
        <div id="aiFaoliyat"></div>
      </div>
    </div>
  </div>`;
};

function aiOrnat() {
  const sel = _id('aiTanla');
  if (sel) sel.onchange = e => { AI_KALIT = e.target.value; aiYangiSuhbat(); };
  const matn = _id('aiMatn');
  if (matn) {
    matn.addEventListener('input', () => aiOlchamla(matn));
    matn.addEventListener('keydown', e => {
      // Enter — yuborish, Shift+Enter — yangi qator (chat oynalarida odatiy)
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); aiYubor(); }
    });
    matn.focus();
  }
  aiTugmaHolat(false);
  aiYangiSuhbat();
  aiFaoliyatChiz(window._aiFaoliyat);
}

/** Har yordamchining o'z salomi va TAKLIF QILINGAN savollari.
 *  Bo'sh oynaga qarab turgan odam nima so'rashni bilmaydi — shuning
 *  uchun bosiladigan namunalar beriladi. */
const AI_NAMUNA = {
  sozlash: {
    salom: 'Тизимни бизнесингизга мослаб бераман. Нима ишлаб чиқарасиз ёки сотасиз?',
    savollar: ['Нон заводимиз бор, кунига 3000 нон ёпамиз',
               'Қандай тайёр соҳа профиллари бор?',
               'Мебель цехи учун тизим ясаб бер'],
  },
  ombor: {
    salom: 'Омбор бўйича савол беринг.',
    savollar: ['Омборда нима бор?', 'Нима тугаяпти?',
               'Қайси буюртмага хомашё етмайди?'],
  },
  moliya: {
    salom: 'Молия бўйича савол беринг.',
    savollar: ['Ким энг кўп қарздор?', 'Пул ҳолати қандай?',
               'Қарз ёшини диаграмма қилиб кўрсат'],
  },
  buyurtma: {
    salom: 'Буюртмалар бўйича савол беринг.',
    savollar: ['Қайси буюртмалар кечикяпти?',
               'Жараёндаги буюртмалар қанча?',
               'Шу буюртмага қанча материал кетади?'],
  },
};

function aiYangiSuhbat() {
  AI_SUHBAT = null;
  const oqim = _id('aiOqim');
  if (oqim) oqim.innerHTML = '';
  const a = AI_ROYXAT.find(x => x.kalit === AI_KALIT);
  const n = AI_NAMUNA[AI_KALIT] || { salom: 'Саволингизни ёзинг.', savollar: [] };
  aiXabar('agent', (a ? a.nom + '.\n\n' : '') + n.salom);

  const quti = _id('aiTaklif');
  if (!quti) return;
  quti.innerHTML = '';
  for (const s of n.savollar) {
    const b = document.createElement('button');
    b.className = 'btn sm ai-namuna';
    b.textContent = s;
    b.onclick = () => { _id('aiMatn').value = s; aiYubor(); };
    quti.appendChild(b);
  }
}

function aiXabar(kim, matn, asboblar, komponentlar) {
  const oqim = _id('aiOqim');
  if (!oqim) return null;
  const div = document.createElement('div');
  div.className = 'ai-xabar ' + (kim === 'user' ? 'meniki' : 'agentniki');
  const p = document.createElement('div');
  p.className = 'ai-matn';
  // textContent — model javobi ham, foydalanuvchi matni ham ishonchsiz
  p.textContent = matn;
  div.appendChild(p);

  // «Nima qildim» izi: qaysi asbob chaqirildi. Foydalanuvchi AI
  // qayerdan ma'lumot olganini ko'rib turishi kerak — aks holda
  // raqamlarga ishonish qiyin.
  if (asboblar && asboblar.length) {
    const iz = document.createElement('div');
    iz.className = 'ai-iz';
    iz.textContent = '⚙ ' + asboblar.join(' · ');
    div.appendChild(iz);
  }
  if (komponentlar && komponentlar.length) {
    const chizilgan = genuiChiz(komponentlar, AI_SUHBAT);
    if (chizilgan) div.appendChild(chizilgan);
  }
  oqim.appendChild(div);
  oqim.scrollTop = oqim.scrollHeight;
  return div;
}

// Asbob nomlarini odam tiliga o'girish — foydalanuvchi «qarzdorlar»
// degan texnik nomni emas, nima bo'layotganini ko'rsin.
const AI_ASBOB_MATNI = {
  qarzdorlar: 'қарзларни кўряпман',
  pul_holati: 'пул ҳолатини оляпман',
  mijoz_hisobi: 'мижоз ҳисобини оляпман',
  ombor_qoldigi: 'омборни текширяпман',
  buyurtmalar: 'буюртмаларни кўряпман',
  buyurtma_retsepti: 'хомашё ҳисобини оляпман',
  sinov_buyurtma: 'синов ҳисоби қиляпман',
  profillarni_kor: 'соҳа профилларини кўряпман',
  modullarni_kor: 'иш тартибларини кўряпман',
  profilni_oqi: 'профилни ўқияпман',
  profil_saqla: 'профилни сақлаяпман',
  profilni_faollashtir: 'профилни фаоллаштиряпман',
  korsat: 'жадвал чизяпман',
};

let AI_BEKOR = null;      // joriy so'rovni to'xtatish uchun

async function aiYubor() {
  if (AI_BAND) return;
  const kirish = _id('aiMatn');
  const matn = (kirish?.value || '').trim();
  if (!matn) return;

  kirish.value = '';
  aiOlchamla(kirish);
  _id('aiTaklif').innerHTML = '';
  aiXabar('user', matn);
  AI_BAND = true;
  aiTugmaHolat(true);

  // Jonli holat ko'rsatadigan «pufakcha»
  const kutish = aiXabar('agent', 'Ўйлаяпман…');
  kutish?.classList.add('ai-kutish');
  const holatMatni = kutish?.querySelector('.ai-matn');
  const qadamlar = [];
  const t0 = Date.now();
  // Soniyalarni sanab turamiz: 20 soniyalik jimlik «qotib qoldi» ga
  // o'xshaydi, o'sib borayotgan raqam esa ishlayotganini bildiradi.
  const soat = setInterval(() => {
    if (!holatMatni) return;
    const sek = Math.round((Date.now() - t0) / 1000);
    const oxirgi = qadamlar.length ? qadamlar[qadamlar.length - 1] : 'Ўйлаяпман';
    holatMatni.textContent = `${oxirgi}… ${sek}s`;
  }, 500);

  AI_BEKOR = new AbortController();
  try {
    const javob = await fetch(API + '/api/agent/oqim', {
      method: 'POST', signal: AI_BEKOR.signal,
      headers: { 'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + TOKEN },
      body: JSON.stringify({ matn, suhbat_id: AI_SUHBAT, agent: AI_KALIT }),
    });
    if (!javob.ok) {
      let izoh = 'Xatolik ' + javob.status;
      try { izoh = (await javob.json()).detail || izoh; } catch (e) { }
      throw new Error(izoh);
    }

    // NDJSON: har qator — bitta hodisa. Qatorlar bo'linib kelishi
    // mumkin, shuning uchun oxirgi to'liqsiz qator buferda qoladi.
    const oquvchi = javob.body.getReader();
    const dekoder = new TextDecoder();
    let bufer = '';
    let yakun = null;

    while (true) {
      const { value, done } = await oquvchi.read();
      if (done) break;
      bufer += dekoder.decode(value, { stream: true });
      const satrlar = bufer.split('\n');
      bufer = satrlar.pop() || '';
      for (const satr of satrlar) {
        if (!satr.trim()) continue;
        let h;
        try { h = JSON.parse(satr); } catch (e) { continue; }
        if (h.tur === 'boshlandi') AI_SUHBAT = h.suhbat_id;
        else if (h.tur === 'asbob') {
          qadamlar.push(AI_ASBOB_MATNI[h.nom] || h.nom);
        } else if (h.tur === 'qayta_urinish') {
          // Javob uzilib qolgan — qisqaroq qilib qayta urinilmoqda
          qadamlar.push('жавобни қисқартириб қайта ёзяпман');
        } else if (h.tur === 'qayta_boshlandi') {
          // Model kvotasi tugab, zaxirasiga o'tildi — foydalanuvchi
          // nega kutayotganini bilsin
          qadamlar.push('заҳира моделга ўтяпман');
        } else if (h.tur === 'xato') {
          throw new Error(h.matn);
        } else if (h.tur === 'yakun') {
          yakun = h;
          if (h.suhbat_id) AI_SUHBAT = h.suhbat_id;
        }
      }
    }

    clearInterval(soat);
    kutish?.remove();
    if (yakun) {
      aiXabar('agent', yakun.javob,
        // `korsat` — foydalanuvchi uchun «asbob» emas, javobning o'zi
        (yakun.izlar || []).map(i => i.asbob).filter(x => x !== 'korsat'),
        yakun.komponentlar);
      aiFaoliyatYangila();
    } else {
      aiXabar('agent', 'Жавоб келмади. Қайта уриниб кўринг.');
    }
  } catch (e) {
    clearInterval(soat);
    kutish?.remove();
    aiXabar('agent', e.name === 'AbortError'
      ? 'Тўхтатилди.'
      : 'Хатолик: ' + (e.message || e));
  } finally {
    clearInterval(soat);
    AI_BAND = false;
    AI_BEKOR = null;
    aiTugmaHolat(false);
    kirish?.focus();
  }
}

/** Yuborish tugmasini «To'xtatish» ga almashtiradi va aksincha. */
function aiTugmaHolat(band) {
  const b = _id('aiYubor');
  if (!b) return;
  b.textContent = band ? 'Тўхтатиш' : 'Юбориш';
  b.classList.toggle('dngr', band);
  b.classList.toggle('pri', !band);
  b.onclick = band ? aiToxtat : aiYubor;
}

function aiToxtat() {
  if (AI_BEKOR) AI_BEKOR.abort();
}

/** Matn maydoni yozilgan matnga qarab o'sadi (3 qatorgacha). */
function aiOlchamla(el) {
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 96) + 'px';
}

async function aiFaoliyatYangila() {
  try { aiFaoliyatChiz(await api('/api/agent/faoliyat')); } catch (e) { /* jim */ }
}

function aiFaoliyatChiz(f) {
  const quti = _id('aiFaoliyat');
  if (!quti || !f) return;
  quti.innerHTML = '';

  const holat = f.holat || {};
  const bayroq = document.createElement('div');
  bayroq.className = 'ai-bayroq ' + (holat.tayyor ? 'ai-b-ok' : 'ai-b-dn');
  bayroq.textContent = holat.tayyor
    ? `● Уланган: ${holat.provayder} · ${holat.model}`
    : '○ Уланмаган — API калит қўйилмаган';
  quti.appendChild(bayroq);

  // HAMMA provayder holati. Bir nechta kalit qo'yilsa hammasi
  // ishlatiladi: birinchisining kvotasi tugasa keyingisiga o'tiladi.
  // Foydalanuvchi qaysi kalit ulangan-u qaysi biri yo'qligini
  // ko'rib turishi kerak.
  if ((holat.provayderlar || []).length) {
    quti.appendChild(el('div', 'ai-kichik', 'API калитлар'));
    for (const p of holat.provayderlar) {
      const q = el('div', 'ai-kalit');
      q.appendChild(el('span', 'ai-kalit-nuqta ' +
        (p.ishlaydi ? 'ai-t-ok' : 'ai-t-mut'), p.ishlaydi ? '●' : '○'));
      q.appendChild(el('span', 'ai-kalit-nom', p.nom));
      q.appendChild(el('span', 'muted ai-kalit-izoh', p.izoh));
      quti.appendChild(q);
    }
    if ((holat.ulangan || []).length > 1) {
      quti.appendChild(el('div', 'muted ai-bosh-izoh',
        'Биттасининг квотаси тугаса кейингисига ўтилади.'));
    }
  }

  // --- AI taklifi bilan bajarilgan o'zgarishlar --------------------
  const sarlavha = document.createElement('div');
  sarlavha.className = 'ai-kichik';
  sarlavha.textContent = 'AI таклифи билан бажарилган ўзгаришлар';
  quti.appendChild(sarlavha);

  if (!(f.amallar || []).length) {
    const bosh = document.createElement('div');
    bosh.className = 'muted ai-bosh-izoh';
    bosh.textContent = 'Ҳозирча йўқ. AI ўзи ҳеч нарса ёзмайди — у таклиф '
      + 'қилади, тугмани сиз босасиз. Бажарилгани шу ерда қолади.';
    quti.appendChild(bosh);
  } else {
    for (const a of f.amallar) {
      const q = document.createElement('div');
      q.className = 'ai-amal';
      const bosh = document.createElement('div');
      bosh.className = 'between';
      bosh.appendChild(el('b', null, a.amal));
      bosh.appendChild(el('span', 'muted ai-vaqt', (a.vaqt || '').slice(0, 16).replace('T', ' ')));
      q.appendChild(bosh);
      q.appendChild(el('div', 'ai-amal-izoh', a.tafsilot));
      q.appendChild(el('div', 'muted ai-vaqt', '👤 ' + a.kim));
      quti.appendChild(q);
    }
  }

  // --- Oxirgi suhbatlar -------------------------------------------
  if ((f.suhbatlar || []).length) {
    const s2 = document.createElement('div');
    s2.className = 'ai-kichik';
    s2.textContent = 'Охирги суҳбатлар';
    quti.appendChild(s2);
    for (const s of f.suhbatlar.slice(0, 6)) {
      const q = el('div', 'ai-suhbat', s.sarlavha);
      q.title = (s.vaqt || '').slice(0, 16).replace('T', ' ');
      quti.appendChild(q);
    }
  }
}
