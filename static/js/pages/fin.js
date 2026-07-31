/* ---- Moliya ---- */
PAGES.fin=async()=>{
  const[deb,cf,cf30,audit]=await Promise.all([api('/api/finance/debtors'),api('/api/finance/cashflow?days=7'),
    api('/api/finance/cashflow?days=30'),api('/api/finance/audit?limit=500')]);
  return `
  <div class="grid g3 mb">
    ${kpi('up','Мижозлар қарзи — жами',mshort(deb.reduce((a,x)=>a+x.debt,0))+" сўм",deb.length+' мижоз','dn')}
    ${kpi('wallet','Пул оқими — 7 kun',mshort(cf.forecast_balance)+" сўм",cf.forecast_balance>=0?'pul yetadi':'етмайди!',cf.forecast_balance>=0?'up':'dn')}
    ${kpi('wallet','Пул оқими — 30 kun',mshort(cf30.forecast_balance)+" сўм",cf30.forecast_balance>=0?'pul yetadi':'етмайди!',cf30.forecast_balance>=0?'up':'dn')}
  </div>
  <div class="glass card mb">
    <h2 class="sec">Қарзлар таҳлили — муддат бўйича</h2>
    <div class="sec-sub">Жами қарз қачондан бери турибди</div>
    <div class="grid g4 mb" style="gap:8px">
      ${['0-15','15-30','30-60','60+'].map(k=>{
        const sum=deb.reduce((a,x)=>a+(x.aging[k]||0),0);
        const cls=k==='0-15'?'ok':k==='15-30'?'warn':'dn';
        return `<div style="text-align:center;padding:12px 6px;border-radius:14px;background:linear-gradient(160deg,rgba(255,255,255,.45),rgba(255,255,255,.2))">
          <span class="tag ${cls}" style="font-size:10px">${k} kun</span>
          <b style="display:block;margin-top:7px;font-size:15px">${sum?mshort(sum):'—'}</b></div>`;}).join('')}
    </div>
    <div class="sec-sub">Яшил — янги қарз (0–15 кун) · Сариқ — 15–30 кун · Қизил — 30 кундан ошган</div>
    <table><thead><tr><th>Мижоз</th><th>Жами қарз</th><th>0–15 kun</th><th>15–30</th><th>30–60</th><th>60+</th><th></th></tr></thead><tbody>
    ${deb.map(x=>`<tr><td><b>${esc(x.company)}</b>${x.blacklisted?' <span class="tag dn">qora ro\'yxat</span>':''}
      ${x.credit_limit&&x.debt>x.credit_limit?' <span class="tag dn">limit oshgan!</span>':''}</td>
      <td><b>${mshort(x.debt)}</b></td>
      ${['0-15','15-30','30-60','60+'].map(k=>`<td>${x.aging[k]>0?`<span class="tag ${agColor(k,x.aging[k])}">${mshort(x.aging[k])}</span>`:'<span class="muted">—</span>'}</td>`).join('')}
      <td>${dl('/api/reports/sverka/'+x.client_id+'.xlsx','Сверка')}
      ${['Rahbar','Buxgalter','Menejer'].includes(ME.role)?`<button class="btn sm pri" onclick="payForm(${x.client_id})">Тўлов</button>`:''}</td></tr>`).join('')||'<tr><td colspan="7" class="muted">Qarzdorlar yo\'q 🎉</td></tr>'}
    </tbody></table>
  </div>
  <div class="glass card mb">
    <h2 class="sec">Ҳисоботлар — 1 босишда юклаб олиш</h2>
    <div class="sec-sub">Excel formatida, hisob-kitob ishlariga tayyor</div>
    <div class="row" style="flex-wrap:wrap;gap:8px">
      ${dl('/api/reports/warehouse.xlsx','📦 Омбор қолдиқлари')}
      ${dl('/api/reports/cash.xlsx','💵 Ходим кассаси')}
      ${dl('/api/reports/payroll.xlsx','👷 Ойлик ведомость')}
      ${dl('/api/reports/purchases.xlsx','🛒 Харидлар (закуп)')}
      ${dl('/api/kassa/export.xlsx','📒 Kassa jurnali')}
    </div>
    <div class="muted" style="font-size:11px;margin-top:8px">Сверка — ҳар мижознинг қаторида · Акт ва Юк хати — буюртма картасида</div>
  </div>
  ${(()=>{
    const byDay={};
    audit.forEach(a=>{const d=a.at.slice(0,10);(byDay[d]=byDay[d]||[]).push(a);});
    const days=Object.keys(byDay).sort().reverse();
    const inner=`<div class="muted" style="font-size:11px;margin-bottom:8px">Жами ${audit.length} амал · кунлар бўйича · пастга сурib кўринг</div>
    <div style="max-height:440px;overflow-y:auto;margin:-4px -4px 0">`+days.map(d=>
      `<div style="font-size:11.5px;font-weight:700;color:var(--primary-deep);padding:9px 4px 5px;
        position:sticky;top:0;background:rgba(255,255,255,.94);backdrop-filter:blur(4px);border-bottom:1px solid var(--hair)">
        ${d} · ${byDay[d].length} амал</div>`+
      byDay[d].map(a=>`<div style="font-size:12px;padding:7px 4px;border-top:1px solid var(--hair)">
        <b>${esc(a.action)}</b> <span class="muted">· ${esc(a.who)} · ${a.at.replace('T',' ').slice(11,16)}</span>
        <div class="muted" style="font-size:11px">${esc(a.detail)}</div></div>`).join('')
    ).join('')+`</div>`;
    return acc(`Амаллар тарихи (${audit.length})`,inner);
  })()}`;
};

