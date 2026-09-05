/* ================= AI AGENT — o'ng tomondagi suhbat oynasi =================
 *
 * Konstruktorning foydalanuvchi yuzi: mijoz biznesini aytadi, agent savol
 * beradi va tizimni yig'adi. Panel HAR SAHIFADA ochiladi — mijoz zakaz
 * ekranini ko'rib turib «bu yerda o'lcham emas, og'irlik bo'lsin» deyishi
 * mumkin, panel alohida sahifa bo'lsa buni qilib bo'lmasdi.
 */

let AGENT_SUHBAT = null;      // joriy suhbat id (null = yangi)
let AGENT_BAND = false;       // javob kutilyaptimi
let AGENT_KALIT = null;       // qaysi bo'lim agenti
let AGENT_ROYXAT = [];        // rolga ochiq agentlar
let AGENT_OPENER = null;      // panel yopilganda fokus qaytadigan element
let AGENT_APP_OLD_INERT = false;
let AGENT_APP_QULFLANGAN = false;

function agentMobilmi(){return matchMedia('(max-width:900px)').matches;}

function agentSemantika(){
  const panel=document.getElementById('agentPanel');
  if(!panel)return;
  const mobil=agentMobilmi();
  panel.setAttribute('role',mobil?'dialog':'complementary');
  if(mobil)panel.setAttribute('aria-modal','true');
  else panel.removeAttribute('aria-modal');
  const app=document.getElementById('app');
  if(panel.classList.contains('ochiq')&&mobil&&app&&!AGENT_APP_QULFLANGAN){
    AGENT_APP_OLD_INERT=app.inert;app.inert=true;AGENT_APP_QULFLANGAN=true;
  }else if((!mobil||!panel.classList.contains('ochiq'))&&app&&AGENT_APP_QULFLANGAN){
    app.inert=AGENT_APP_OLD_INERT;AGENT_APP_QULFLANGAN=false;
  }
}

function agentFocusables(){
  const panel=document.getElementById('agentPanel');
  if(!panel)return[];
  return [...panel.querySelectorAll('button:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')]
    .filter(el=>el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden');
}

function agentPanelYasa() {
  if (document.getElementById('agentPanel')) return;

  const panel = document.createElement('div');
  panel.id = 'agentPanel';
  panel.className = 'agent-panel';
  panel.setAttribute('aria-hidden','true');
  panel.setAttribute('aria-labelledby','agentNom');
  panel.innerHTML = `
    <div class="agent-head">
      <div style="flex:1;min-width:0">
        <div class="agent-title" id="agentNom">Ёрдамчи</div>
        <select class="agent-tanla" id="agentTanla" aria-label="AI yordamchini tanlash"></select>
        <div class="agent-sub" id="agentHolat" aria-live="polite">tekshirilmoqda…</div>
      </div>
      <div class="agent-head-btns">
        <button type="button" class="agent-icon" id="agentYangi" title="Yangi suhbat" aria-label="Yangi suhbat">${icon('pencil',15)}</button>
        <button type="button" class="agent-icon" id="agentYop" title="Yopish" aria-label="AI yordamchini yopish">${icon('x',15)}</button>
      </div>
    </div>
    <div class="agent-oqim" id="agentOqim" role="log" aria-live="polite" aria-relevant="additions"></div>
    <div class="agent-kirish">
      <textarea id="agentMatn" rows="2" aria-label="AI yordamchiga savol"
        placeholder="Savolingizni yozing…"></textarea>
      <button type="button" class="btn agent-yubor" id="agentYubor">Yuborish</button>
    </div>`;
  document.body.appendChild(panel);

  const tugma = document.createElement('button');
  tugma.id = 'agentOch';
  tugma.className = 'agent-och';
  tugma.title = 'Sozlash yordamchisi';
  tugma.type = 'button';
  tugma.setAttribute('aria-label','AI yordamchini ochish');
  tugma.setAttribute('aria-controls','agentPanel');
  tugma.setAttribute('aria-expanded','false');
  tugma.innerHTML = icon('ai', 24);
  document.body.appendChild(tugma);

  tugma.onclick = () => agentOchYop(true);
  document.getElementById('agentYop').onclick = () => agentOchYop(false);
  document.getElementById('agentYangi').onclick = agentYangiSuhbat;
  document.getElementById('agentTanla').onchange = e => {
    AGENT_KALIT = e.target.value;
    agentYangiSuhbat();   // boshqa yordamchi — boshqa suhbat
  };
  document.getElementById('agentYubor').onclick = agentYubor;
  document.getElementById('agentMatn').addEventListener('keydown', e => {
    // Enter — yuborish, Shift+Enter — yangi qator. Chat oynalarida
    // odatiy xulq; aks holda uzun matn yozayotgan odam adashadi.
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); agentYubor(); }
  });
  panel.addEventListener('keydown',e=>{
    if(e.key==='Escape'){
      e.preventDefault();
      agentOchYop(false);
      return;
    }
    if(e.key!=='Tab'||!agentMobilmi())return;
    const focusable=agentFocusables();
    if(!focusable.length)return;
    const first=focusable[0],last=focusable[focusable.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  });
  agentSemantika();
  matchMedia('(max-width:900px)').addEventListener('change',agentSemantika);
}

function agentOchYop(ochiq) {
  const panel=document.getElementById('agentPanel');
  const tugma=document.getElementById('agentOch');
  if(ochiq&&!panel.classList.contains('ochiq'))AGENT_OPENER=document.activeElement;
  panel.classList.toggle('ochiq', ochiq);
  tugma.setAttribute('aria-expanded',String(ochiq));
  const qurTugma=document.getElementById('qurChatTugma');
  if(qurTugma)qurTugma.setAttribute('aria-expanded',String(ochiq));
  // Panel holati BODY ga ham chiqariladi: layout (sidebar yig'ilishi,
  // kontentning qayta joylashuvi) shu sinfga tayanadi. `:has()` ga
  // tayanib bo'lmadi — panel qayta ochilganda brauzer `.main` uchun
  // uslubni qayta hisoblamadi (o'lchab tekshirildi: 438px -> 0px).
  document.body.classList.toggle('ai-ochiq', ochiq);
  tugma.classList.toggle('yashir', ochiq);
  agentSemantika();
  if (ochiq) {
    panel.setAttribute('aria-hidden','false');
    agentHolatniOl();
    document.getElementById('agentMatn').focus();
  } else {
    if(AGENT_OPENER&&AGENT_OPENER.isConnected)AGENT_OPENER.focus({preventScroll:true});
    panel.setAttribute('aria-hidden','true');
    AGENT_OPENER=null;
  }
}

async function agentHolatniOl() {
  const el = document.getElementById('agentHolat');
  try {
    const h = await api('/api/agent/holat');
    el.textContent = h.tayyor ? (h.provayder + ' · ' + h.model) : h.izoh;
    el.className = 'agent-sub' + (h.tayyor ? '' : ' agent-ogoh');
    document.getElementById('agentYubor').disabled = !h.tayyor;

    AGENT_ROYXAT = h.agentlar || [];
    const sel = document.getElementById('agentTanla');
    // Yordamchi BITTA (2026-08-20) — tanlash ro'yxati keraksiz,
    // faqat joy egallaydi. Bitta bo'lsa yashiriladi.
    // Yordamchi bitta bo'lsa tanlash ro'yxati yashiriladi va uning
    // o'rniga oddiy sarlavha chiqadi. Ilgari ikkalasi ham yo'q edi —
    // panel boshida faqat model nomi turardi, kim bilan gaplashayotgani
    // bilinmasdi.
    const nomEl = document.getElementById('agentNom');
    const bitta = AGENT_ROYXAT.length <= 1;
    if (sel) sel.style.display = bitta ? 'none' : '';
    if (nomEl) {
      nomEl.style.display = bitta ? '' : 'none';
      if (bitta && AGENT_ROYXAT.length) nomEl.textContent = AGENT_ROYXAT[0].nom;
    }
    if (sel && sel.options.length !== AGENT_ROYXAT.length) {
      sel.innerHTML = AGENT_ROYXAT
        .map(a => `<option value="${a.kalit}">${a.nom}</option>`).join('');
      // Rolga ochiq birinchisi — Rahbarda «sozlash», sklad mudirida «ombor»
      if (!AGENT_KALIT && AGENT_ROYXAT.length) {
        AGENT_KALIT = AGENT_ROYXAT[0].kalit;
        agentYangiSuhbat();
      }
      sel.value = AGENT_KALIT || '';
    }
  } catch (e) { el.textContent = 'holatni olib bo\'lmadi'; }
}

// Har yordamchining o'z salomi — foydalanuvchi nima so'rashi mumkinligini
// darrov bilsin, bo'sh oynaga qarab turmasin.
const AGENT_SALOM = {
  sozlash: 'Tizimni biznesingizga moslab beraman.\n\nNima ishlab chiqarasiz yoki sotasiz?',
  ombor:   'Ombor bo\'yicha savol bering.\n\nMasalan: «Nima tugayapti?» yoki «25-zakazga nima yetmaydi?»',
  moliya:  'Moliya bo\'yicha savol bering.\n\nMasalan: «Kim qarzdor?» yoki «Pul holati qanday?»',
  buyurtma:'Buyurtmalar bo\'yicha savol bering.\n\nMasalan: «Qaysi zakazlar kechikyapti?»',
  // Yagona yordamchi (2026-08-20 dan) — hamma bo'limni ko'radi, shuning
  // uchun salomi ham nima so'rash mumkinligini ko'rsatib turishi kerak.
  // Ilgari bu kalit ro'yxatda yo'q edi va quruq «Savolingizni yozing»
  // chiqardi — foydalanuvchi nima so'rashini bilmasdi.
  yordamchi:
    'Savol bering — buyurtma, ombor, pul, xodim, harid: hammasini ko\'raman.\n\n' +
    'Masalan:\n' +
    '• «Kim qancha qarzdor?»\n' +
    '• «Nima tugayapti?»\n' +
    '• «Bu oy qancha kirim bo\'ldi?»\n' +
    '• «Qaysi buyurtmalar kechikyapti?»',
};

function agentYangiSuhbat() {
  AGENT_SUHBAT = null;
  document.getElementById('agentOqim').innerHTML = '';
  const a = AGENT_ROYXAT.find(x => x.kalit === AGENT_KALIT);
  // Nom faqat bir nechta yordamchi bo'lganda qo'shiladi. Bitta bo'lsa u
  // panel sarlavhasida turibdi — salomda takrorlash ortiqcha.
  const nom = (a && AGENT_ROYXAT.length > 1) ? a.nom + '.\n\n' : '';
  agentXabarQosh('agent', nom +
    (AGENT_SALOM[AGENT_KALIT] || 'Savolingizni yozing.'));
}

// **Qalin** yozuvni chizadi. Model markdown ishlatadi, ilgari esa matn
// to'g'ridan-to'g'ri `textContent` ga qo'yilardi va ekranda xom
// yulduzchalar ko'rinardi: «**Xon xonim** va **Bahrom** kabi».
//
// HTML QURILMAYDI. `innerHTML` ishlatilmaydi — matn tugunlari va
// `<strong>` elementlari qo'lda yasaladi. Agent javobi ham, foydalanuvchi
// matni ham ishonchsiz manba, shuning uchun xavfsizlik xossasi
// o'zgarmasdan qoladi.
function matnniChiz(idish, matn) {
  idish.textContent = '';
  const bolaklar = String(matn == null ? '' : matn).split(/\*\*(.+?)\*\*/gs);
  bolaklar.forEach((b, i) => {
    if (!b) return;
    if (i % 2 === 1) {                      // qavs ichidagi — qalin
      const q = document.createElement('strong');
      q.textContent = b;
      idish.appendChild(q);
    } else {
      idish.appendChild(document.createTextNode(b));
    }
  });
}

function agentXabarQosh(kim, matn, asboblar, komponentlar, suhbatId) {
  const oqim = document.getElementById('agentOqim');
  const div = document.createElement('div');
  div.className = 'agent-xabar ' + (kim === 'user' ? 'meniki' : 'agentniki');
  // textContent — HTML sifatida talqin qilinmasin. Agent javobi ham,
  // foydalanuvchi matni ham ishonchsiz manba hisoblanadi.
  const p = document.createElement('div');
  p.className = 'agent-matn';
  matnniChiz(p, matn);
  div.appendChild(p);
  // GenUI: agent chizgan komponentlar matndan KEYIN keladi. Matn qisqa
  // xulosa, tafsilot esa jadval/ko'rsatkich/tasdiq tugmasi ko'rinishida.
  if (komponentlar && komponentlar.length) {
    const chizilgan = genuiChiz(komponentlar, suhbatId);
    if (chizilgan) div.appendChild(chizilgan);
  }
  if (asboblar && asboblar.length) {
    const iz = document.createElement('div');
    iz.className = 'agent-iz';
    iz.innerHTML = icon('gear', 12) + ' ' + esc(asboblar.join(' · '));
    div.appendChild(iz);
  }
  oqim.appendChild(div);
  oqim.scrollTop = oqim.scrollHeight;
  return div;
}

async function agentYubor() {
  if (AGENT_BAND) return;
  const kirish = document.getElementById('agentMatn');
  const matn = kirish.value.trim();
  if (!matn) return;

  kirish.value = '';
  agentXabarQosh('user', matn);
  AGENT_BAND = true;
  document.getElementById('agentYubor').disabled = true;

  // Kutish pufagi — endi JONLI qadam ko'rsatadi (muzlab turmaydi).
  const kutish = agentXabarQosh('agent', 'O\'ylayapman…');
  kutish.classList.add('agent-kutish');
  const holatEl = kutish.querySelector('.agent-matn') || kutish;
  const t0 = Date.now();
  const qadamlar = [];
  const soat = setInterval(() => {
    const sek = Math.round((Date.now() - t0) / 1000);
    const oxirgi = qadamlar.length ? qadamlar[qadamlar.length - 1] : 'O\'ylayapman';
    holatEl.textContent = `${oxirgi}… ${sek}s`;
  }, 500);

  const asbobMatni = (nom) =>
    (typeof AI_ASBOB_MATNI !== 'undefined' && AI_ASBOB_MATNI[nom]) || nom;

  try {
    // OQIM: bloklaydigan /api/agent/xabar o'rniga /api/agent/oqim.
    // Foydalanuvchi har qadamni DARROV ko'radi — javob tugashini
    // muzlab kutmaydi. Bu tezlikni sezilarli oshiradi (his-tuyg'uda).
    const javob = await fetch(API + '/api/agent/oqim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + TOKEN },
      body: JSON.stringify({ matn, suhbat_id: AGENT_SUHBAT, agent: AGENT_KALIT }),
    });
    if (!javob.ok) {
      let izoh = 'Xatolik ' + javob.status;
      try { izoh = (await javob.json()).detail || izoh; } catch (e) {}
      throw new Error(izoh);
    }

    // NDJSON — har qator bitta hodisa; oxirgi to'liqsiz qator buferda.
    const oquvchi = javob.body.getReader();
    const dekoder = new TextDecoder();
    let bufer = '', yakun = null;
    while (true) {
      const { value, done } = await oquvchi.read();
      if (done) break;
      bufer += dekoder.decode(value, { stream: true });
      const satrlar = bufer.split('\n');
      bufer = satrlar.pop() || '';
      for (const satr of satrlar) {
        if (!satr.trim()) continue;
        let h; try { h = JSON.parse(satr); } catch (e) { continue; }
        if (h.tur === 'boshlandi') { if (h.suhbat_id) AGENT_SUHBAT = h.suhbat_id; }
        else if (h.tur === 'asbob') qadamlar.push(asbobMatni(h.nom));
        else if (h.tur === 'qayta_urinish') qadamlar.push('javobni qisqartiryapman');
        else if (h.tur === 'qayta_boshlandi') qadamlar.push('zaxira modelga o\'tyapman');
        else if (h.tur === 'xato') throw new Error(h.matn);
        else if (h.tur === 'yakun') { yakun = h; if (h.suhbat_id) AGENT_SUHBAT = h.suhbat_id; }
      }
    }

    clearInterval(soat);
    kutish.remove();
    if (!yakun) { agentXabarQosh('agent', 'Javob kelmadi. Qayta urinib ko\'ring.'); return; }

    const izlar = yakun.izlar || [];
    agentXabarQosh('agent', yakun.javob,
      izlar.map(i => i.asbob).filter(x => x !== 'korsat'),
      yakun.komponentlar, yakun.suhbat_id);

    // Agent profil YOKI bo'limlarni o'zgartirgan bo'lsa — menyu va
    // sahifani yangilaymiz, aks holda eski holat ekranda qoladi.
    if (izlar.some(i => ['profilni_faollashtir', 'profil_saqla',
        'bolimlarni_sozla', 'rollarni_sozla'].includes(i.asbob))) {
      if (typeof navYukla === 'function') { try { await navYukla(); } catch (e) {} }
      if (typeof renderNav === 'function') renderNav();
      if (typeof _renderPage === 'function' && typeof PAGE === 'string') _renderPage(PAGE);
    }
  } catch (e) {
    clearInterval(soat);
    kutish.remove();
    agentXabarQosh('agent', 'Xatolik: ' + (e.message || e));
  } finally {
    AGENT_BAND = false;
    document.getElementById('agentYubor').disabled = false;
    kirish.focus();
  }
}
