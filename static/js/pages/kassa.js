/* ---- Kassa jurnali (kirim-chiqim daftari) ---- */
PAGES.kassa=async()=>{
  window._kassaFirm='';
  return kassaView('');
};
async function kassaView(firm){
  const d=await api('/api/kassa'+(firm?'?firm='+encodeURIComponent(firm):''));
  window._kassaFirms=d.firms;
  const byDay={};
  d.entries.forEach(e=>{(byDay[e.entry_at]=byDay[e.entry_at]||[]).push(e)});
  const days=Object.keys(byDay).sort().reverse();
  return `
  <div class="grid g3 mb">
    ${kpi('up','Жами кирим',mshort(d.kirim)+" сўм",d.usd_kirim?('+ '+d.usd_kirim+' $'):'','up')}
    ${kpi('flag','Жами чиқим',mshort(d.chiqim)+" сўм",d.usd_chiqim?('+ '+d.usd_chiqim+' $'):'','dn')}
    ${kpi('wallet','Баланс',mshort(d.balans)+" сўм",d.balans>=0?'плюс':'минус',d.balans>=0?'up':'dn')}
  </div>
  <div class="between mb" style="flex-wrap:wrap;gap:8px">
    <div class="chips" style="margin:0">
      <button class="fchip ${!firm?'on':''}" onclick="switchFirm('')">Ҳаммаси</button>
      ${d.firms.map(fm=>`<button class="fchip ${firm===fm?'on':''}" onclick="switchFirm('${esc(fm)}')">${esc(fm)}</button>`).join('')}
    </div>
    <div class="row">
      ${['Rahbar','Buxgalter'].includes(ME.role)?`
        <button class="btn pri sm" onclick="kassaForm('Kirim')">↓ Кирим</button>
        <button class="btn sm dngr" onclick="kassaForm('Chiqim')">↑ Чиқим</button>`:''}
      ${dl('/api/kassa/export.xlsx'+(firm?'?firm='+encodeURIComponent(firm):''),'Excel')}
    </div>
  </div>
  <div class="glass card">
    ${days.map(day=>{
      const list=byDay[day];
      const dk=list.filter(x=>x.direction==='Kirim'&&x.currency==="so'm").reduce((a,x)=>a+x.amount,0);
      const dc=list.filter(x=>x.direction==='Chiqim'&&x.currency==="so'm").reduce((a,x)=>a+x.amount,0);
      return `<div style="padding:6px 0">
      <div class="between" style="font-size:11px;color:var(--ink-3);padding:6px 2px;border-bottom:1px solid var(--hair)">
        <b>${day}</b><span>${dk?'+'+mshort(dk):''} ${dc?' −'+mshort(dc):''}</span></div>
      ${list.map(e=>`<div class="between" style="padding:8px 2px;border-bottom:1px solid var(--hair);gap:8px">
        <span style="flex:1"><b style="font-size:13px">${esc(e.who)}</b>
          ${!window._kassaFirm&&e.firm?`<span class="tag mut" style="font-size:9px;padding:1px 6px">${esc(e.firm)}</span>`:''}
          ${e.note?`<div class="muted" style="font-size:10.5px">${esc(e.note)}</div>`:''}</span>
        <b style="color:${e.direction==='Kirim'?'var(--ok)':'var(--danger)'};font-variant-numeric:tabular-nums;white-space:nowrap">
          ${e.direction==='Kirim'?'+':'−'}${e.currency==='USD'?e.amount+' $':money(e.amount)}</b>
        ${ME.role==='Rahbar'?`<button class="btn sm ghost" onclick="delKassa(${e.id})">✕</button>`:''}
      </div>`).join('')}</div>`;}).join('')||`<div class="muted" style="text-align:center;padding:30px">
      <div style="font-size:28px">💵</div><b style="display:block;margin:6px 0">Журнал бўш</b>
      <div style="font-size:12px">«Kirim» yoki «Chiqim» tugmasi bilan birinchi yozuvni kiriting</div></div>`}
  </div>`;
}
async function switchFirm(fm){
  window._kassaFirm=fm;
  document.getElementById('content').innerHTML='<div class="muted" style="padding:30px;text-align:center">Yuklanmoqda…</div>';
  document.getElementById('content').innerHTML='<div class="page show">'+await kassaView(fm)+'</div>';
}
function kassaForm(dir){
  const firms=window._kassaFirms&&window._kassaFirms.length?window._kassaFirms:['Asosiy'];
  const defFirm=FIRM||window._kassaFirm||firms[0];
  modal(`<h2 class="sec mb">${dir==='Kirim'?'↓ Кирим (pul keldi)':'↑ Чиқим (pul ketdi)'}</h2>
  <label class="fl">${dir==='Kirim'?'Kimdan':'Kimga - nimaga'}</label>
  <input class="fld" id="k_who" placeholder="${dir==='Kirim'?'mijoz/manba nomi':'masalan: Remont, Avans, Kley...'}"/>
  <label class="fl">Изоҳ (ixtiyoriy)</label><input class="fld" id="k_note"/>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Сумма</label><input class="fld" id="k_amount" inputmode="numeric" oninput="pulFmt(this)"/></div>
    <div><label class="fl">Валюта</label><select class="fld" id="k_cur"><option value="so'm">сўм</option><option value="USD">USD</option></select></div>
  </div>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Цех / филиал</label>
      <input class="fld" id="k_firm" list="firmList" value="${esc(defFirm)}"/>
      <datalist id="firmList">${firms.map(fm=>`<option>${esc(fm)}</option>`).join('')}</datalist></div>
    <div><label class="fl">Сана</label><input class="fld" id="k_date" type="date" value="${new Date().toISOString().slice(0,10)}"/></div>
  </div>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveKassa('${dir}')">Сақлаш</button></div>`);
}
async function saveKassa(dir){
  try{const r=await post('/api/kassa',{direction:dir,who:f('k_who'),note:f('k_note'),
    amount:fnum('k_amount'),currency:f('k_cur'),firm:f('k_firm'),entry_at:f('k_date')});
    closeModal();toast('o','check',kir(dir)+' ёзилди',money(fnum('k_amount')||0));
    if(r&&r.ogoh)setTimeout(()=>toast('w','alertic','Диққат — икки марта саналмасин',r.ogoh),400);
    go('kassa');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}
async function delKassa(id){
  if(!confirm('Ёзувни ўчирасизми?'))return;
  try{await api('/api/kassa/'+id,{method:'DELETE'});go('kassa');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}

