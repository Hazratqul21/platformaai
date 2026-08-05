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

function agentPanelYasa() {
  if (document.getElementById('agentPanel')) return;

  const panel = document.createElement('div');
  panel.id = 'agentPanel';
  panel.className = 'agent-panel';
  panel.innerHTML = `
    <div class="agent-head">
      <div style="flex:1;min-width:0">
        <select class="agent-tanla" id="agentTanla"></select>
        <div class="agent-sub" id="agentHolat">tekshirilmoqda…</div>
      </div>
      <div class="agent-head-btns">
        <button class="agent-icon" id="agentYangi" title="Yangi suhbat">✎</button>
        <button class="agent-icon" id="agentYop" title="Yopish">✕</button>
      </div>
    </div>
    <div class="agent-oqim" id="agentOqim"></div>
    <div class="agent-kirish">
      <textarea id="agentMatn" rows="2"
        placeholder="Biznesingizni ayting — masalan: «Non zavodimiz bor, kuniga 3000 non yopamiz»"></textarea>
      <button class="btn agent-yubor" id="agentYubor">Yuborish</button>
    </div>`;
  document.body.appendChild(panel);

  const tugma = document.createElement('button');
  tugma.id = 'agentOch';
  tugma.className = 'agent-och';
  tugma.title = 'Sozlash yordamchisi';
  tugma.textContent = '✦';
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
}

function agentOchYop(ochiq) {
  document.getElementById('agentPanel').classList.toggle('ochiq', ochiq);
  document.getElementById('agentOch').classList.toggle('yashir', ochiq);
  if (ochiq) {
    agentHolatniOl();
    document.getElementById('agentMatn').focus();
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
    if (sel.options.length !== AGENT_ROYXAT.length) {
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
};

function agentYangiSuhbat() {
  AGENT_SUHBAT = null;
  document.getElementById('agentOqim').innerHTML = '';
  const a = AGENT_ROYXAT.find(x => x.kalit === AGENT_KALIT);
  agentXabarQosh('agent', (a ? a.nom + '.\n\n' : '') +
    (AGENT_SALOM[AGENT_KALIT] || 'Savolingizni yozing.'));
}

function agentXabarQosh(kim, matn, asboblar) {
  const oqim = document.getElementById('agentOqim');
  const div = document.createElement('div');
  div.className = 'agent-xabar ' + (kim === 'user' ? 'meniki' : 'agentniki');
  // textContent — HTML sifatida talqin qilinmasin. Agent javobi ham,
  // foydalanuvchi matni ham ishonchsiz manba hisoblanadi.
  const p = document.createElement('div');
  p.className = 'agent-matn';
  p.textContent = matn;
  div.appendChild(p);
  if (asboblar && asboblar.length) {
    const iz = document.createElement('div');
    iz.className = 'agent-iz';
    iz.textContent = '⚙ ' + asboblar.join(' · ');
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
  const kutish = agentXabarQosh('agent', 'O\'ylayapman…');
  kutish.classList.add('agent-kutish');
  document.getElementById('agentYubor').disabled = true;

  try {
    const j = await api('/api/agent/xabar', 'POST',
      { matn, suhbat_id: AGENT_SUHBAT, agent: AGENT_KALIT });
    AGENT_SUHBAT = j.suhbat_id;
    kutish.remove();
    agentXabarQosh('agent', j.javob,
      (j.izlar || []).map(i => i.asbob));
    // Agent profilni o'zgartirgan bo'lishi mumkin — sahifani yangilaymiz,
    // aks holda ekranda eski soha maydonlari turaveradi.
    if ((j.izlar || []).some(i =>
        i.asbob === 'profilni_faollashtir' || i.asbob === 'profil_saqla')) {
      if (typeof route === 'function') route();
    }
  } catch (e) {
    kutish.remove();
    agentXabarQosh('agent', 'Xatolik: ' + (e.message || e));
  } finally {
    AGENT_BAND = false;
    document.getElementById('agentYubor').disabled = false;
    kirish.focus();
  }
}
