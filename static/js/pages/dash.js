/* ---- Dashboard ---- */
PAGES.dash=async()=>{
  const d=await api('/api/finance/dashboard');
  const hour=new Date().getHours();
  const salom=hour<12?t('good_morning'):hour<18?t('good_day'):t('good_evening');
  const maxS=Math.max(...d.sales_series.map(x=>x.sales),1);
  const flowCls=d.cashflow.forecast_balance>=0?'ok':'dn';
  return `
  <div class="between mb" style="padding:2px 4px">
    <div><span style="font-family:var(--serif);font-size:20px;font-weight:700">${salom}, ${esc(ME.name)}!</span>
    <div class="muted" style="font-size:12px;margin-top:2px">${uzDate(new Date())}</div></div>
  </div>
  ${d.low_stock.length?(()=>{const a=d.low_stock[0];const kg=Number(a.stock_kg||0);
    return `<div class="alert d glass mb" style="border-radius:16px"><div class="ai">${icon('alertic',16)}</div>
    <div><b>${esc(a.grade)} — ${kg<0?'омбор қарзда':t('paper_enough_for').replace('{days}', Math.max(1,Math.round(a.days_left)))}</b>
    <p>${t('restock_warehouse')} — ${kg<0?Math.abs(kg).toFixed(0)+' кг етишмаяпти':t('left_in_stock').replace('{amount}', kg.toFixed(0)+' кг')}</p></div></div>`;})():''}
  <div class="row mb" style="gap:8px;overflow-x:auto;padding:2px;-webkit-overflow-scrolling:touch">
    ${quickActions().slice(0,5).map(q=>`<button class="btn" style="flex:none" onclick="QUICK[${QUICK.indexOf(q)}].run()">${q.i} ${q.t}</button>`).join('')}
  </div>
  <div class="grid g4 mb">
    ${kpi('wallet',t('today_sales'),mshort(d.today_sales)+" сўм",'','')}
    ${kpi('chart',t('month_sales'),mshort(d.month_sales)+" сўм",(d.growth_percent>=0?'+':'')+d.growth_percent+'%',d.growth_percent>=0?'up':'dn')}
    ${kpi('up',t('client_debt'),mshort(d.total_debit)+" сўм",t('they_will_pay'),'dn')}
    ${kpi('flag',t('our_debt'),mshort(d.total_credit)+" сўм",t('to_suppliers'),'dn')}
  </div>
  <div class="split mb">
    <div class="glass card">
      <div class="between mb"><h2 class="sec">${t('sales_dynamics')}</h2></div>
      <div class="bars">${d.sales_series.map(x=>`<div class="bar"><div class="col" style="height:${Math.max(x.sales/maxS*100,3)}%"></div><small>${x.month.slice(5)}${t('month_suffix')}</small></div>`).join('')}</div>
      <div class="between" style="margin-top:14px;font-size:12px;flex-wrap:wrap">
        <span class="muted">${t('profit_share')}</span>
        ${d.margins.map(x=>`<span><b>${x.margin}%</b> <span class="muted">${x.month.slice(5)}</span></span>`).join('')}
      </div>
    </div>
    <div class="glass card">
      <h2 class="sec mb">Огоҳлантиришлар</h2>
      <div style="display:flex;flex-direction:column;gap:9px">
        ${d.low_stock.length?d.low_stock.map(a=>{
          const kg=Number(a.stock_kg||0);
          return alertBox(kg<0?'d':'w','alertic',kg<0?'Хомашё қарзда (минусда)':'Хомашё тугаяпти',
            `${esc(a.grade)} · ${a.grammage} гр — ${kg.toFixed(0)} кг${kg<0?' (омборга кирим қилиниши шарт)':`, ~${a.days_left} кунга етади`}`);
        }).join(''):alertBox('o','check','Хомашё етарли','Минимал қолдиқ чегарасидан юқори')}
        ${alertBox(flowCls==='ok'?'o':'d','wallet','Пул оқими — 7 кун',`Кирим ${mshort(d.cashflow.expected_in)} − Чиқим ${mshort(d.cashflow.expected_out)} = <b>${mshort(d.cashflow.forecast_balance)} сўм</b>`)}
        ${alertBox('w','clock','Жараёндаги буюртмалар',`Кутишда: ${d.order_counts['Kutishda']} · Цехда: ${d.order_counts['Sexda kesilmoqda']} · Омборда: ${d.order_counts['Omborga tushdi']}`)}
        ${(d.kassa_kirim||d.kassa_chiqim)?alertBox(d.kassa_balans>=0?'o':'w','wallet','Касса журнали',`Кирим ${mshort(d.kassa_kirim)} − Чиқим ${mshort(d.kassa_chiqim)} = <b>${mshort(d.kassa_balans)} сўм</b>`):''}
      </div>
    </div>
  </div>
  ${acc('Энг катта қарздорлар',`
    <div class="between" style="margin-bottom:4px"><span></span><button class="btn sm ghost" onclick="go('fin')">Барчаси →</button></div>
    ${d.top_debtors.map(x=>{
      const days=x.aging['60+']>0?'60+ кун':x.aging['30-60']>0?'30–60 кун':x.aging['15-30']>0?'15–30 кун':'янги қарз';
      const cls=x.aging['60+']>0||x.aging['30-60']>0?'dn':x.aging['15-30']>0?'warn':'ok';
      return `<div class="row" style="padding:10px 2px;border-top:1px solid var(--hair);gap:12px;cursor:pointer" onclick="openClient(${x.client_id})">
      <div style="width:36px;height:36px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;font-weight:700;flex:none">${esc(x.company[0])}</div>
      <div style="flex:1"><b style="font-size:13px">${esc(x.company)}</b>
        <div class="muted" style="font-size:10.5px"><span class="tag ${cls}" style="font-size:9.5px;padding:1px 7px">${days}</span>${x.blacklisted?' <span class="tag dn" style="font-size:9.5px;padding:1px 7px">блокланган</span>':''}</div></div>
      <b style="font-variant-numeric:tabular-nums">${mshort(x.debt)}</b></div>`;}).join('')||'<div class="muted">Қарздор йўқ 🎉</div>'}`)}`;
};

