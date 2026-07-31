/* ---- CRM ---- */
PAGES.crm = async () => {
    const cs = await api('/api/clients');
    window.crmData = cs;
    window._clients = cs;
    window._postRender = crmRender;
    if(!window._firms){ try{ window._firms = await api('/api/kassa/firms'); }catch(e){ window._firms=[]; } }
    if(window._crmView===undefined)window._crmView='card';
    return `
    <div class="glass card mb" style="padding:12px">
      <div class="row" style="gap:8px;align-items:center">
        <input class="fld" id="crmSearch" style="margin:0;flex:1"
          placeholder="🔍 Мижозни қидириш — номи, телефон ёки СТИР бўйича…"
          oninput="crmRender()" />
        <button class="btn ${window._crmView==='table'?'pri':''}" onclick="crmToggleView()" title="Жадвал/карта">
          ${window._crmView==='table'?'▦ Жадвал':'▤ Карта'}</button>
        ${['Rahbar','Menejer'].includes(ME.role)?`<button class="btn" onclick="crmAddModal()">${icon('plus',15)} Янги мижоз</button>`:''}
      </div>
      <div class="muted" style="font-size:11.5px;margin-top:6px" id="crmCount"></div>
    </div>
    <div id="crmList"></div>`;
};
window.crmToggleView=()=>{ window._crmView=window._crmView==='table'?'card':'table'; go('crm'); };

window.crmLoad = async () => {
    const res = await api('/api/clients');
    window.crmData = res; window._clients = res;
    crmRender();
};

window.crmRender = () => {
    const lst = _id('crmList');
    if(!lst) return;
    const q = (_id('crmSearch')?.value || '').trim().toLowerCase();
    const arr = (window.crmData||[]).filter(c =>
        !q ||
        (c.company||'').toLowerCase().includes(q) ||
        (c.contact||'').toLowerCase().includes(q) ||
        (c.phone||'').toLowerCase().includes(q) ||
        (c.inn||'').toLowerCase().includes(q)
    );
    const cnt = _id('crmCount');
    if(cnt) cnt.textContent = q
        ? `«${q}» бўйича ${arr.length} та мижоз топилди (жами ${window.crmData.length} та)`
        : `Жами ${window.crmData.length} та мижоз — ${window._crmView==='table'?'қаторни':'картани'} босинг, тўлиқ деталлари очилади`;

    // ---- Jadval ko'rinishi (rasmdagi kabi) ----
    if(window._crmView==='table'){
      lst.className='glass card';
      lst.style.padding='0';lst.style.overflowX='auto';
      lst.innerHTML=`<table style="font-size:12px;min-width:640px">
        <thead><tr><th>Компания</th><th>Контакт</th><th>Телефон</th><th>Фирма</th>
          <th style="text-align:right">Буюртма</th><th style="text-align:right">Қарз</th><th></th></tr></thead>
        <tbody>${arr.map(c=>`<tr style="cursor:pointer" onclick="openClient(${c.id})">
          <td><b>${esc(c.company)}</b> ${c.category==='VIP'?'<span class="tag pri" style="font-size:9px">VIP</span>':''}</td>
          <td class="muted">${esc(c.contact||'—')}</td>
          <td class="muted">${esc(c.phone||'—')}</td>
          <td>${c.firm?'<span class="tag mut" style="font-size:9.5px">'+esc(c.firm)+'</span>':'<span class="muted" style="font-size:10px">—</span>'}</td>
          <td style="text-align:right">${c.orders_count}</td>
          <td style="text-align:right;color:${c.debt>0?'var(--danger)':'var(--ok)'}"><b>${mshort(c.debt)}</b></td>
          <td>${['Rahbar','Menejer','Buxgalter'].includes(ME.role)?`<button class="btn sm ghost" title="Таҳрирлаш" onclick='event.stopPropagation();crmAddModal(${JSON.stringify(c).replace(/'/g,"&#39;")})'>✎</button>`:''}</td>
        </tr>`).join('')||'<tr><td colspan="7" class="muted" style="text-align:center;padding:20px">Мижоз топилмади</td></tr>'}</tbody>
      </table>`;
      return;
    }
    lst.className='grid g3'; lst.style.padding='';lst.style.overflowX='';
    lst.innerHTML = arr.map(c => `
    <div class="glass card" style="padding:14px">
        <div class="between" style="cursor:pointer" onclick="openClient(${c.id})">
            <b style="font-size:13.5px">${esc(c.company)}</b>
            <span class="tag ${c.category === 'VIP' ? 'pri' : 'mut'}">${kir(c.category)}</span>
        </div>
        <div class="muted" style="font-size:11px;margin:4px 0">${esc(c.contact||'')}${c.phone ? ' · '+esc(c.phone) : ''}</div>
        <div style="font-size:10.5px;margin-bottom:4px">${c.firm
            ? '<span class="tag mut">🏭 '+esc(c.firm)+'</span>'
            : '<span class="tag warn" title="Фирмаси белгиланмаган — иккала фирмада кўринади">⚠️ фирма белгиланмаган</span>'}</div>
        <div class="between" style="margin-top:6px;font-size:12.5px;cursor:pointer" onclick="openClient(${c.id})">
            <span class="muted">Қарз</span>
            <b style="color:${c.debt>0?'var(--danger)':'var(--ok)'}">${mshort(c.debt)}</b>
        </div>
        <div class="between" style="font-size:11.5px">
            <span class="muted">Буюртмалар</span><span>${c.orders_count} та</span>
        </div>
        <div class="row" style="gap:5px;margin-top:8px">
          <button class="btn sm pri" style="flex:1;justify-content:center" onclick="openClient(${c.id})">📋 Деталлари</button>
          ${['Rahbar','Menejer','Buxgalter'].includes(ME.role)?`<button class="btn sm ghost" title="Таҳрирлаш" onclick='crmAddModal(${JSON.stringify(c).replace(/'/g,"&#39;")})'>✎</button>`:''}
        </div>
    </div>`).join('') || `<div class="glass card muted" style="grid-column:1/-1;text-align:center;padding:26px">
        <div style="font-size:26px">🔍</div><b style="display:block;margin:6px 0">Мижоз топилмади</b>
        <div style="font-size:12px">Бошқа ном, телефон ёки СТИР билан қидириб кўринг</div></div>`;
};

window.crmFilter = () => crmRender();

window.crmAddModal = (c) => {
    c = c || {};
    const firms = window._firms || [];
    openModal(`
    <h3>${c.id?'Мижозни таҳрирлаш':'Янги мижоз'}</h3>
    <label class="fl">Компания номи</label>
    <input class="fld" id="crm_comp" value="${esc(c.company||'')}" />
    <label class="fl">Контакт шахс</label>
    <input class="fld" id="crm_cont" value="${esc(c.contact||'')}" />
    <label class="fl">Телефон</label>
    <input class="fld" id="crm_ph" value="${esc(c.phone||'')}" />
    <label class="fl">Қайси фирма мижози</label>
    <select class="fld" id="crm_firm">
      <option value="">— белгиланмаган (иккала фирмада кўринади) —</option>
      ${firms.map(x=>`<option value="${esc(x)}" ${(c.firm||window.FIRM)===x?'selected':''}>🏭 ${esc(x)}</option>`).join('')}
    </select>
    <label class="fl">Тоифа (нархга таъсир қилади)</label>
    <select class="fld" id="crm_cat">
      ${['Yangi','Standart','VIP'].map(x=>`<option value="${x}" ${(c.category||'Yangi')===x?'selected':''}>${kir(x)}</option>`).join('')}
    </select>
    <label class="fl">Бошланғич қарз (тизимдан олдинги, ихтиёрий)</label>
    <input class="fld" id="crm_open" inputmode="numeric" value="${c.opening_balance?Number(Math.round(c.opening_balance)).toLocaleString('ru-RU'):''}" placeholder="масалан: 9 710 850" oninput="pulFmt(this)"/>
    <div class="muted" style="font-size:10.5px;margin-top:2px">1.07.26 гача бўлган қарз. Манфий (−) = биз мижозга қарздормиз (аванс).</div>
    <div class="flx" style="gap:10px;margin-top:16px;">
        <button class="btn ghost" style="flex:1" onclick="closeModal()">${t('cancel')}</button>
        <button class="btn primary" style="flex:1" onclick="crmSave(${c.id||0})">${t('save')}</button>
    </div>
    `);
};

window.crmSave = async (id) => {
    let data = {
        company: _id('crm_comp').value.trim(),
        contact: _id('crm_cont').value.trim(),
        phone: _id('crm_ph').value.trim(),
        category: _id('crm_cat').value,
        firm: _id('crm_firm').value,
        opening_balance: +(_id('crm_open').value.replace(/\s/g,''))||0,
        opening_date: '2026-07-01'
    };
    if(!data.company) return toast("Компания номи киритилмади", "err");
    try{
      if(id) await api('/api/clients/'+id, {method:'PUT', body:JSON.stringify(data)});
      else   await api('/api/clients', 'POST', data);
      toast("Сақланди");
      closeModal();
      await crmLoad();
    }catch(e){ toast(e.message, "err"); }
};

window.crmView = (id) => openClient(id);

/* ---- Mijoz detalizatsiyasi — daftar ko'rinishi (mollar | kassa | qarz) ---- */
async function openClient(id){
  const d = await api('/api/clients/'+id+'/detalizatsiya');
  const rows = Math.max(d.mollar.length, d.kassa.length, 1);
  let body = '';
  for(let i=0;i<rows;i++){
    const o = d.mollar[i], kas = d.kassa[i];
    const opening = o && o.status==='opening';
    body += `<tr${opening?' style="background:rgba(249,217,122,.25)"':''}>
      <td class="muted" style="font-size:10.5px">${o?o.sana:''}</td>
      <td>${o?(opening?'<b>—</b>':'<b>#'+o.nakladnoy+'</b>'):''}</td>
      <td${opening?' style="font-style:italic;font-weight:600"':''}>${o?esc(o.mahsulot||'—'):''}</td>
      <td class="muted" style="font-size:10.5px">${o?esc(o.olchov):''}</td>
      <td style="text-align:right">${o&&o.dona!==''?new Intl.NumberFormat('ru-RU').format(o.dona):''}</td>
      <td style="text-align:right">${o&&o.narxi!==''?new Intl.NumberFormat('ru-RU').format(Math.round(o.narxi)):''}</td>
      <td style="text-align:right"><b>${o?new Intl.NumberFormat('ru-RU').format(Math.round(o.jami)):''}</b></td>
      <td class="muted" style="font-size:10.5px;border-left:2px solid var(--hair)">${kas?kas.sana:''}</td>
      <td style="text-align:right;color:var(--ok)"><b>${kas?new Intl.NumberFormat('ru-RU').format(Math.round(kas.summa)):''}</b></td>
      <td class="muted" style="font-size:10.5px">${kas?kir(kas.tolov_turi):''}</td>
    </tr>`;
  }
  modal(`<h2 class="sec">${esc(d.company)}</h2>
  <div class="muted" style="font-size:12px;margin:4px 0 12px">${esc(d.contact||'')}${d.phone?' · '+esc(d.phone):''}${d.inn?' · STIR: '+esc(d.inn):''}</div>
  <div class="grid g3 mb" style="gap:8px">
    <div style="text-align:center"><div class="muted" style="font-size:10px">МОЛ БЕРИЛДИ</div><b>${mshort(d.jami_mol)}</b></div>
    <div style="text-align:center"><div class="muted" style="font-size:10px">ПУЛ ОЛИНДИ</div><b style="color:var(--ok)">${mshort(d.jami_tolov)}</b></div>
    <div style="text-align:center"><div class="muted" style="font-size:10px">ҚАРЗ</div><b style="color:${d.qarz>0?'var(--danger)':'var(--ok)'}">${mshort(d.qarz)}</b></div>
  </div>
  <div class="row mb" style="flex-wrap:wrap;gap:6px">
    ${dl('/api/reports/sverka/'+d.client_id+'.xlsx','Сверка акти')}
    ${['Rahbar','Buxgalter','Menejer'].includes(ME.role)?`<button class="btn sm pri" onclick="payForm(${d.client_id})">💵 Тўлов қабул қилиш</button>`:''}
  </div>
  ${(d.tayyor&&d.tayyor.length)?`<div class="glass card mb" style="padding:10px;border:1px solid var(--primary-deep)">
    <div class="between" style="margin-bottom:6px"><b style="font-size:12.5px">📦 Топширишга тайёр (${d.tayyor.length} та)</b>
      <span class="muted" style="font-size:10.5px">белгилаб бирга топширинг</span></div>
    ${d.tayyor.map(o=>`<label class="between" style="font-size:12px;padding:5px 0;border-top:1px solid var(--hair);cursor:pointer">
      <span><input type="checkbox" class="tp_chk" value="${o.id}" data-sum="${o.summa}" onchange="tpUpdate()"/>
        <b>#${o.id}</b> ${esc(o.product_name||o.tur)} <span class="muted">${new Intl.NumberFormat('ru-RU').format(o.qolgan_qty)} дона</span></span>
      <b>${mshort(o.summa)}</b></label>`).join('')}
    <div class="between" style="margin-top:8px">
      <span class="muted" style="font-size:11.5px">Танланган: <b id="tp_count">0</b> та · <b id="tp_sum">0</b></span>
      <button class="btn sm pri" onclick="topshirBatch(${d.client_id})">📤 Бирга топшириш</button></div>
  </div>`:''}
  <div style="overflow-x:auto">
  <table style="font-size:11px;min-width:660px">
    <thead>
      <tr><th colspan="7" style="text-align:center;background:var(--hair)">БЕРИЛГАН МАҲСУЛОТЛАР</th>
          <th colspan="3" style="text-align:center;background:var(--hair);border-left:2px solid var(--ink-2)">КАССА (келган пул)</th></tr>
      <tr><th>Сана</th><th>Nak №</th><th>Маҳсулот</th><th>Ўлчов/формат</th><th style="text-align:right">дона</th>
          <th style="text-align:right">Нархи</th><th style="text-align:right">Жами</th>
          <th style="border-left:2px solid var(--hair)">Сана</th><th style="text-align:right">Сумма</th><th>Тўлов тури</th></tr>
    </thead>
    <tbody>${body}</tbody>
    <tfoot>
      <tr style="border-top:2px solid var(--ink-2)">
        <td colspan="6"><b>Жами маҳсулот суммаси</b></td>
        <td style="text-align:right"><b>${new Intl.NumberFormat('ru-RU').format(Math.round(d.jami_mol))}</b></td>
        <td style="border-left:2px solid var(--hair)"><b>Жами тўлов</b></td>
        <td style="text-align:right;color:var(--ok)"><b>${new Intl.NumberFormat('ru-RU').format(Math.round(d.jami_tolov))}</b></td>
        <td></td>
      </tr>
      <tr><td colspan="7"></td>
        <td style="border-left:2px solid var(--hair)"><b>ҚАРЗ</b></td>
        <td colspan="2" style="text-align:right;font-size:14px;color:${d.qarz>0?'var(--danger)':'var(--ok)'}">
          <b>${new Intl.NumberFormat('ru-RU').format(Math.round(d.qarz))}</b></td>
      </tr>
    </tfoot>
  </table></div>
  ${d.mollar.length?'':'<div class="muted" style="font-size:12px;margin-top:8px">Ҳали мол берилмаган (фақат цехга берилган ёки етказилган буюртмалар ҳисобга киради)</div>'}`, true);
}
/* ---- Yig'ib topshirish (bir nechta buyurtma birga) ---- */
function tpUpdate(){
  const chk=[...document.querySelectorAll('.tp_chk:checked')];
  const sum=chk.reduce((a,x)=>a+(+x.dataset.sum||0),0);
  const c=_id('tp_count'), s=_id('tp_sum');
  if(c)c.textContent=chk.length;
  if(s)s.textContent=mshort(sum);
}
async function topshirBatch(cid){
  const ids=[...document.querySelectorAll('.tp_chk:checked')].map(x=>+x.value);
  if(!ids.length)return toast('w','alertic','Танланмади','Камида битта буюртма белгиланг');
  const sum=[...document.querySelectorAll('.tp_chk:checked')].reduce((a,x)=>a+(+x.dataset.sum||0),0);
  modal(`<h2 class="sec">Йиғиб топшириш — ${ids.length} та буюртма</h2>
  <div class="between mb" style="font-size:13.5px"><span>Жами сумма</span><b style="color:var(--primary-deep)">${money(sum)}</b></div>
  <label class="fl">Мижоз ҳозир берган пул (сўм)</label>
  <input class="fld" id="tb_amount" inputmode="numeric" value="0" placeholder="0 — қарзга берилди" oninput="pulFmt(this)"/>
  <div class="row" style="gap:6px;margin:6px 0">
    <button class="btn sm" onclick="_id('tb_amount').value=${Math.round(sum)}">Тўлиқ тўлади</button>
    <button class="btn sm" onclick="_id('tb_amount').value=0">Қарзга берилди</button></div>
  <label class="fl">Тўлов тури</label>
  <select class="fld" id="tb_method"><option value="Naqd">Нақд</option><option value="Karta">Карта</option><option value="O'tkazma">Ўтказма</option></select>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick='tbSave(${cid},${JSON.stringify(ids)})'>📤 Топшириш</button></div>`);
}
async function tbSave(cid,ids){
  try{
    const r=await post('/api/orders/topshir-batch',{order_ids:ids,paid_amount:fnum('tb_amount')||0,method:f('tb_method')});
    closeModal();
    toast('o','check',r.count+' та буюртма топширилди','қарз: '+money(r.client_debt));
    openClient(cid);
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function reorder(oid){
  const qty=prompt('Янги тираж (дона):');if(!qty)return;
  try{const o=await post('/api/orders/'+oid+'/reorder?qty='+(+qty),{});
    closeModal();toast('o','check','Такрорий буюртма яратилди','#'+o.id+' · '+money(o.total));go('orders');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function payForm(cid){
  modal(`<h2 class="sec mb">Тўлов қабул қилиш</h2>
  ${cid?'':`<label class="fl">Мижоз</label><select class="fld" id="p_client">
    ${(window._clients||[]).map(c=>`<option value="${c.id}">${esc(c.company)}${c.debt>0?' — қарзи '+mshort(c.debt):''}</option>`).join('')}</select>`}
  <label class="fl">Сумма (сўм)</label><input class="fld" id="p_amount" inputmode="numeric" oninput="pulFmt(this)"/>
  <label class="fl">Усул</label><select class="fld" id="p_method"><option value="Naqd">Нақд</option><option value="Karta">Карта</option><option value="O'tkazma">Ўтказма</option></select>
  <label class="fl">Изоҳ</label><input class="fld" id="p_note"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="savePay(${cid||0})">Сақлаш</button></div>`);
}
async function savePay(cid){
  try{await post('/api/finance/payments',{client_id:cid||+f('p_client'),amount:fnum('p_amount'),method:f('p_method'),note:f('p_note')});
    closeModal();toast('o','check','Тўлов сақланди',money(fnum('p_amount')||0));go(PAGE);
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function qaPay(){closeModal();if(!window._clients)window._clients=await api('/api/clients');payForm(null);}
