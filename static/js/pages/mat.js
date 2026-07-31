/* ---- Materiallar katalogi ---- */
PAGES.mat=async()=>{
  const[mats,cats,units]=await Promise.all([api('/api/catalog/materials'),
    api('/api/catalog/categories'),api('/api/catalog/units')]);
  window._cats=cats;window._units=units;window._mats=mats;window._matFilter='';window._postRender=renderMats;
  return `
  <div class="glass card mb" style="padding:12px">
    <div class="row" style="gap:8px;align-items:center">
      <input class="fld" id="matSearch" style="margin:0;flex:1"
        placeholder="🔍 Маҳсулотни қидириш — номи, марка ёки граммаж бўйича…" oninput="renderMats()"/>
      <button class="btn pri" onclick="renderMats()">${icon('boxIn',15)} Қидириш</button>
      ${['Rahbar','Sklad mudiri'].includes(ME.role)?`<button class="btn" onclick="matForm()">${icon('plus',15)} Янги материал</button>`:''}
    </div>
    <div class="muted" style="font-size:11.5px;margin-top:6px" id="matCount"></div>
  </div>
  <div class="chips"><button class="fchip on" onclick="window._matFilter='';document.querySelectorAll('.chips .fchip').forEach(b=>b.classList.remove('on'));this.classList.add('on');renderMats()">Ҳаммаси</button>
    ${cats.map(c=>`<button class="fchip" onclick="window._matFilter='${esc(c.name)}';document.querySelectorAll('.chips .fchip').forEach(b=>b.classList.remove('on'));this.classList.add('on');renderMats()">${esc(c.name)}</button>`).join('')}</div>
  <div class="grid g3" id="matCards"></div>`;
};
function renderMats(){
  const box=document.getElementById('matCards');if(!box)return;
  const q=(document.getElementById('matSearch')?.value||'').trim().toLowerCase();
  const list=window._mats.filter(x=>
    (!window._matFilter||x.category===window._matFilter) &&
    (!q || (x.name||'').toLowerCase().includes(q)
        || (x.marka||'').toLowerCase().includes(q)
        || (x.grammaj||'').toLowerCase().includes(q)
        || (x.manufacturer||'').toLowerCase().includes(q)));
  const cnt=document.getElementById('matCount');
  if(cnt)cnt.textContent=q?`«${q}» бўйича ${list.length} та топилди (жами ${window._mats.length} та)`
                          :`Жами ${window._mats.length} та материал`;
  box.innerHTML=list.map(x=>`<div class="glass card" style="padding:14px">
    <div class="between"><b style="font-size:13.5px">${esc(x.name)}${x.grammaj?' <span class="muted" style="font-size:11px">'+esc(x.grammaj)+'</span>':''}</b>
      <span class="tag mut">${kir(x.category)}</span></div>
    ${x.marka||x.manufacturer?`<div class="muted" style="font-size:11px;margin-top:2px">${esc(x.marka)} ${x.manufacturer?'· '+esc(x.manufacturer):''}</div>`:''}
    <div class="between" style="margin-top:8px;font-size:12.5px"><span class="muted">Қолдиқ</span>
      <b style="color:${x.min_stock>0&&x.stock_qty<=x.min_stock?'var(--danger)':'var(--ink)'}">${new Intl.NumberFormat('ru-RU').format(x.stock_qty)} ${esc(x.unit)}</b></div>
    <div class="between" style="font-size:11.5px"><span class="muted">Охирги нарх</span><span>${money(x.last_price)}/${esc(x.unit)}</span></div>
    ${['Rahbar','Sklad mudiri'].includes(ME.role)?`<div class="row" style="margin-top:8px;gap:5px">
      <button class="btn sm ghost" onclick='matForm(${JSON.stringify(x).replace(/'/g,"&#39;")})'>✎</button>
      <button class="btn sm pri" onclick="zakupForm(${x.id})">📥 Харид</button></div>`:''}
  </div>`).join('')||'<div class="glass card muted" style="grid-column:1/-1;text-align:center;padding:30px"><div style="font-size:28px">📦</div><b style="display:block;margin:6px 0">Материал йўқ</b><div style="font-size:12px">«Янги материал» тугмаси билан қоғоз, картон, клей... қўшинг</div></div>';
}
function matForm(x){
  x=x||{};
  modal(`<h2 class="sec mb">${x.id?'Материални таҳрирлаш':'Янги материал'}</h2>
  <label class="fl">Бўлим</label>
  <select class="fld" id="m_cat">${window._cats.map(c=>`<option value="${esc(c.name)}" ${x.category===c.name?'selected':''}>${kir(c.name)}</option>`).join('')}</select>
  <label class="fl">Номи (масалан: Silver pak)</label><input class="fld" id="m_name" value="${esc(x.name||'')}"/>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Граммаж (қоғоз учун)</label><input class="fld" id="m_gr" value="${esc(x.grammaj||'')}" placeholder="140 гр"/></div>
    <div><label class="fl">Ўлчов бирлиги</label><select class="fld" id="m_unit">${window._units.map(u=>`<option ${(x.unit||'kg')===u.name?'selected':''}>${esc(u.name)}</option>`).join('')}</select></div>
  </div>
  <div class="grid g2" style="gap:8px">
    <div><label class="fl">Марка (ихтиёрий)</label><input class="fld" id="m_marka" value="${esc(x.marka||'')}"/></div>
    <div><label class="fl">Ишлаб чиқарувчи</label><input class="fld" id="m_manuf" value="${esc(x.manufacturer||'')}"/></div>
  </div>
  <label class="fl">Минимал қолдиқ (огоҳлантириш учун)</label><input class="fld" id="m_min" type="number" value="${x.min_stock||0}"/>
  <div class="row" style="margin-top:16px;justify-content:flex-end">
    <button class="btn" onclick="closeModal()">Бекор</button>
    <button class="btn pri" onclick="saveMat(${x.id||0})">Сақлаш</button></div>`);
}
async function saveMat(id){
  const body={name:f('m_name'),category:f('m_cat'),grammaj:f('m_gr'),unit:f('m_unit'),
    marka:f('m_marka'),manufacturer:f('m_manuf'),min_stock:+f('m_min')||0};
  if(!body.name)return toast('w','alertic','Диққат','Материал номи мажбурий');
  try{await(id?api('/api/catalog/materials/'+id,{method:'PUT',body:JSON.stringify(body)}):post('/api/catalog/materials',body));
    closeModal();toast('o','check','Сақланди',body.name);go('mat');
  }catch(e){toast('d','alertic','Хатолик',e.message);}
}

