/* ---- Ombor ---- */
PAGES.wh=async()=>{
  const[raw,fin,sups,inv]=await Promise.all([api('/api/warehouse/raw'),api('/api/warehouse/finished'),
    api('/api/warehouse/suppliers'),api('/api/warehouse/inventory')]);
  window._sups=sups;
  return `
  ${raw.alerts.length?`<div class="mb" style="display:flex;flex-direction:column;gap:8px">${raw.alerts.map(a=>alertBox('d','alertic','Минимал қолдиқ!',`${a.grade} (${a.grammage} g): ${a.stock_kg.toFixed(1)} кг — тахминан ${a.days_left} кунга етади`)).join('')}</div>`:''}
  <div class="between mb"><h2 class="sec">Хомашё омбори — партиялар</h2>
    ${['Rahbar','Sklad mudiri'].includes(ME.role)?`<div class="row" style="flex-wrap:wrap"><button class="btn pri sm" onclick="lotForm()">${icon('plus',13)} Кирим</button>
    <button class="btn sm" onclick="supForm()">🚚 Етказиб берувчи</button>
    <button class="btn sm" onclick="invForm()">📋 Саноқ</button>${dl('/api/reports/warehouse.xlsx','Excel')}</div>`:dl('/api/reports/warehouse.xlsx','Excel')}</div>
  ${!raw.groups.length?`<div class="glass card mb" style="text-align:center;padding:30px">
    <div style="font-size:30px">📦</div><b style="display:block;margin:8px 0 4px">Омбор ҳали бўш</b>
    <div class="muted" style="font-size:12px;margin-bottom:12px">Аввал етказиб берувчи қўшинг, кейин қоғоз киримини киритинг</div>
    ${['Rahbar','Sklad mudiri'].includes(ME.role)?`<button class="btn pri sm" onclick="supForm()">🚚 Етказиб берувчи қўшиш</button>`:''}
  </div>`:''}
  <div class="grid g2 mb">
  ${raw.groups.map(g=>`<div class="glass card">
    <div class="between"><b>${g.grade} · ${g.grammage} g</b><span class="tag ${g.stock_kg>3000?'ok':g.stock_kg>800?'warn':'dn'}">${g.stock_kg.toFixed(1)} kg</span></div>
    <div class="muted" style="font-size:11px;margin:4px 0 8px">Қолдиқ қиймати: ${mshort(g.value)} сўм</div>
    ${g.lots.filter(l=>l.remaining_kg>0).map(l=>`<div class="between" style="font-size:11.5px;padding:5px 0;border-top:1px solid var(--hair)">
      <span><b>${l.lot_no}</b> <span class="muted">· ${esc(l.supplier)} · ${l.received_at}</span></span>
      <span>${l.remaining_kg.toFixed(1)}/${l.qty_kg.toFixed(1)} kg <span class="muted">@${new Intl.NumberFormat('ru-RU').format(l.price_per_kg)}</span></span></div>`).join('')||'<div class="muted" style="font-size:11px">Партиялар тугаган</div>'}
  </div>`).join('')}
  </div>
  <div class="split mb">
    <div class="glass card"><h2 class="sec mb">Тайёр маҳсулот омбори</h2>
      <table><thead><tr><th>Буюртма</th><th>Ўлчам</th><th>Сони</th><th>Сумма</th></tr></thead><tbody>
      ${fin.map(x=>`<tr><td><b>#${x.order_id}</b><div class="muted" style="font-size:10px">${esc(x.company)}</div></td>
        <td>${x.size}<div class="muted" style="font-size:10px">${x.layers}q · ${x.grade}</div></td><td>${x.qty}</td><td>${mshort(x.total)}</td></tr>`).join('')||'<tr><td colspan="4" class="muted">Бўш — ҳаммаси етказилган</td></tr>'}
      </tbody></table></div>
    <div class="glass card"><h2 class="sec mb">Охирги инвентаризациялар</h2>
      ${inv.slice(0,6).map(r=>`<div class="between" style="font-size:12px;padding:6px 0;border-top:1px solid var(--hair)">
        <span><b>${r.grade}</b> <span class="muted">· ${r.checked_at}</span></span>
        <span class="tag ${Math.abs(r.diff_kg)<1?'ok':r.diff_kg<0?'dn':'warn'}">${r.diff_kg>0?'+':''}${r.diff_kg.toFixed(1)} kg</span></div>`).join('')||'<div class="muted" style="font-size:12px">Ҳали ўтказилмаган</div>'}
    </div>
  </div>
  <h2 class="sec mb">Етказиб берувчилар — мол олдик / пул бердик</h2>
  <div class="grid g3">
  ${sups.map(sp=>`<div class="glass card">
    <div class="between"><b>${esc(sp.name)}</b>
      <span class="tag ${sp.kind==='Pechat'?'pri':'mut'}" style="font-size:9.5px">${sp.kind==='Pechat'?'🖨 Печат':sp.kind==='Boshqa'?'Бошқа':'📄 Қоғоз'}</span></div>
    <div class="muted" style="font-size:11px;margin:2px 0 8px">${esc(sp.phone)}
      ${['Rahbar','Sklad mudiri','Buxgalter'].includes(ME.role)?`<span style="cursor:pointer;float:right" title="Таҳрирлаш" onclick='supForm(${JSON.stringify(sp).replace(/'/g,"&#39;")})'>✎</span>`:''}</div>
    <div class="between" style="font-size:12px"><span class="muted">Мол олдик</span><b>${mshort(sp.got)}</b></div>
    <div class="between" style="font-size:12px"><span class="muted">Пул бердик</span><b style="color:var(--ok)">${mshort(sp.paid)}</b></div>
    <div class="between" style="font-size:13px;border-top:1px solid var(--hair);padding-top:5px;margin-top:5px">
      <span><b>${sp.avans>0?'Аванcимиз':'Қарзимиз'}</b></span>
      <b style="color:${sp.debt>0?'var(--danger)':sp.avans>0?'var(--primary-deep)':'var(--ok)'}">${sp.avans>0?mshort(sp.avans):mshort(sp.debt)}</b></div>
    ${sp.avans>0?`<div class="muted" style="font-size:10.5px;margin-top:3px">Ортиқча берилган пул — кейинги молдан чегирилади</div>`:''}
    ${sp.schedule.map(sc=>`<div class="between" style="font-size:11px;margin-top:5px"><span class="muted">📅 ${sc.due_date}</span><span>${mshort(sc.amount)} ${['Rahbar','Buxgalter'].includes(ME.role)?`<button class="btn sm ghost" onclick="paySup(${sp.id},${sc.amount},${sc.id})">тўлаш</button>`:''}</span></div>`).join('')}
    ${['Rahbar','Buxgalter','Sklad mudiri'].includes(ME.role)?`<button class="btn sm pri" style="width:100%;justify-content:center;margin-top:8px" onclick='supPayForm(${JSON.stringify(sp).replace(/'/g,"&#39;")})'>💵 Пул бериш</button>`:''}
  </div>`).join('')||'<div class="glass card muted" style="grid-column:1/-1;text-align:center">Етказиб берувчи йўқ</div>'}
  </div>`;
};
/* ---- Yetkazib beruvchiga pul berish (qarzdan ko'p bo'lsa — avans) ---- */
function supPayForm(sp){
  modal(`<h2 class="sec">Пул бериш — ${esc(sp.name)}</h2>
  <div class="glass card mb" style="padding:10px;background:var(--hair);margin-top:8px">
    <div class="between" style="font-size:12.5px"><span>Ундан олинган мол</span><b>${money(sp.got)}</b></div>
    <div class="between" style="font-size:12.5px"><span>Унга берилган пул</span><b style="color:var(--ok)">${money(sp.paid)}</b></div>
    <div class="between" style="font-size:13.5px;border-top:1px solid var(--ink-2);margin-top:6px;padding-top:6px">
      <b>${sp.avans>0?'Бизнинг аванcимиз':'Қарзимиз'}</b>
      <b style="color:${sp.debt>0?'var(--danger)':'var(--primary-deep)'}">${sp.avans>0?money(sp.avans):money(sp.debt)}</b></div>
  </div>
  ${sp.debt<=0?alertBox('w','alertic','Бу етказиб берувчида қарзимиз йўқ',
      "Агар харидни «Нақд» қилиб киритган бўлсангиз — пул аллақачон ҳисобга олинган, "+
      "яна ёзсангиз икки марта саналади. Пулни алоҳида берган бўлсангиз: аввал Харид бўлимида "+
      "ўша харидни «Қарз» қилиб тузатинг, кейин шу ерда пулни ёзинг."):''}
  <label class="fl">Берилаётган сумма (сўм)</label>
  <input class="fld" id="sp_amount" type="number" value="${sp.debt>0?Math.round(sp.debt):''}"/>
  ${sp.debt>0?`<div class="row" style="gap:6px;margin:6px 0">
    <button class="btn sm" onclick="_id('sp_amount').value=${Math.round(sp.debt)}">Қарзни тўлиқ ёпиш</button></div>`:''}
  <label class="fl">Изоҳ</label><input class="fld" id="sp_note" placeholder="масалан: терминалдан, қоғоз учун"/>
  <div class="muted" style="font-size:11px;margin-top:8px">Қарздан кўп берсангиз — ортиқчаси аванс бўлиб қолади ва кейинги молдан чегирилади.</div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="supPaySave(${sp.id})">Бериш</button></div>`);
}
async function supPaySave(sid){
  const amount=+f('sp_amount')||0;
  if(!(amount>0))return toast('w','alertic','Сумма киритилмади',"0 дан катта сон ёзинг");
  try{
    const r=await post('/api/warehouse/suppliers/pay',{supplier_id:sid,amount:amount,note:f('sp_note')});
    closeModal();
    toast('o','check','Пул берилди',money(amount)+(r.avans>0?" · аванcимиз: "+money(r.avans):" · қарз: "+money(r.debt)));
    go('wh');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function supForm(sp){
  sp=sp||{};
  modal(`<h2 class="sec mb">${sp.id?'Етказиб берувчини таҳрирлаш':'Янги етказиб берувчи'}</h2>
  <label class="fl">Номи (компания)</label><input class="fld" id="sp_name" value="${esc(sp.name||'')}"/>
  <label class="fl">Телефон</label><input class="fld" id="sp_phone" value="${esc(sp.phone||'')}" placeholder="+998 xx xxx xx xx"/>
  <label class="fl">Тури</label>
  <select class="fld" id="sp_kind">
    <option value="Qog'oz" ${(sp.kind||"Qog'oz")==="Qog'oz"?'selected':''}>Қоғоз/материал етказиб берувчи</option>
    <option value="Pechat" ${sp.kind==='Pechat'?'selected':''}>Печат — кўчада принт қиладиган фирма</option>
    <option value="Boshqa" ${sp.kind==='Boshqa'?'selected':''}>Бошқа</option>
  </select>
  <div class="muted" style="font-size:11px;margin-top:4px">Печат фирмалари билан ҳам худди қоғоз фирмалари каби ҳисоб-китоб (қарз/аванс/пул бериш) юритилади.</div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveSup(${sp.id||0})">Сақлаш</button></div>`);
}
async function saveSup(id){
  const body={name:f('sp_name'),phone:f('sp_phone'),kind:f('sp_kind')};
  try{
    if(id)await api('/api/warehouse/suppliers/'+id,{method:'PUT',body:JSON.stringify(body)});
    else await post('/api/warehouse/suppliers',body);
    closeModal();toast('o','check','Сақланди',f('sp_name'));window._sups=null;go('wh');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function lotForm(){
  if(!window._sups||!window._sups.length){toast('w','alertic','Аввал етказиб берувчи қўшинг','Кирим партия кимдан келганини билиши керак');supForm();return;}
  modal(`<h2 class="sec mb">Хомашё кирими (янги партия)</h2>
  <label class="fl">Етказиб берувчи</label><select class="fld" id="l_sup">${window._sups.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('')}</select>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Марка</label><input class="fld" id="l_grade" placeholder="Масалан: K1, K2..." /></div>
    <div><label class="fl">Граммаж</label><input class="fld" id="l_grammage" type="number" placeholder="Масалан: 120" /></div>
  </div>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Миқдор, кг</label><input class="fld" id="l_qty" type="number" step="0.1" /></div>
    <div><label class="fl">Нарх, сўм/кг</label><input class="fld" id="l_price" type="number"/></div>
  </div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveLot()">Кирим қилиш</button></div>`);
}
async function saveLot(){
  try{const r=await post('/api/warehouse/raw',{supplier_id:+f('l_sup'),grade:f('l_grade'),grammage:+f('l_grammage'),qty_kg:+f('l_qty'),price_per_kg:+f('l_price')});
    closeModal();toast('o','check','Лот киритилди',r.lot_no);go('wh');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
function invForm(){
  modal(`<h2 class="sec mb">Инвентаризация (саноқ)</h2>
  <div class="sec-sub">Ҳақиқий ўлчов киритилади — фарқ автомат актлаштирилади</div>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Марка</label><input class="fld" id="i_grade" placeholder="Масалан: K1, K2..." /></div>
    <div><label class="fl">Граммаж</label><input class="fld" id="i_grammage" type="number" placeholder="Масалан: 120" /></div>
  </div>
  <label class="fl">Ҳақиқий қолдиқ, кг</label><input class="fld" id="i_actual" type="number" step="0.1"/>
  <label class="fl">Изоҳ</label><input class="fld" id="i_note"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveInv()">Актлаштириш</button></div>`);
}
async function saveInv(){
  try{const r=await post('/api/warehouse/inventory',{grade:f('i_grade'),grammage:+f('i_grammage'),actual_kg:+f('i_actual'),note:f('i_note')});
    closeModal();toast(Math.abs(r.diff_kg)<1?'o':'w','check','Инвентаризация',`Тизим: ${r.system_kg.toFixed(1)} кг · Факт: ${r.actual_kg} кг · Фарқ: ${r.diff_kg>0?'+':''}${r.diff_kg.toFixed(1)} кг`);go('wh');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function paySup(sid,amount,schId){
  if(!confirm('Тўловни тасдиқлайсизми? '+money(amount)))return;
  try{await post('/api/warehouse/suppliers/pay',{supplier_id:sid,amount:amount,schedule_id:schId,note:'Grafik bo\'yicha'});
    toast('o','check','Тўланди',money(amount));go('wh');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}

