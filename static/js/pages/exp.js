/* ---- Cex Rasxodi (Xarajatlar) ---- */
PAGES.exp = async () => {
    setTitle("Цех харажатлари", "Цехдаги кунлик харажатлар");
    
    let html = `
    <div class="flx" style="justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3>Харажатлар</h3>
        <button class="btn" onclick="expAddModal()">+ Янги харажат</button>
    </div>
    <div class="glass" style="padding:16px;">
        <table class="tbl">
            <thead>
                <tr>
                    <th>Сана</th>
                    <th>Нимага (Изоҳ)</th>
                    <th>Сумма</th>
                </tr>
            </thead>
            <tbody id="expList"></tbody>
        </table>
    </div>
    `;
    content.innerHTML = html;
    await expLoad();
};

window.expLoad = async () => {
    let res = await api('/api/hr/cash');
    if(res) {
        let tbody = _id('expList');
        if(!tbody) return;
        
        let arr = res.filter(x => x.kind === 'Xarajat');
        tbody.innerHTML = arr.map(e => `
            <tr>
                <td>${e.entry_at.substring(0, 10)}</td>
                <td><b>${esc(e.note || '-')}</b></td>
                <td><b style="color:var(--red)">${money(e.amount)}</b></td>
            </tr>
        `).join('');
        if(arr.length === 0) tbody.innerHTML = `<tr><td colspan="3" class="empty">Топилмади</td></tr>`;
    }
};

window.expAddModal = () => {
    openModal(`
    <h3>Янги харажат</h3>
    <label class="fl">Сумма (сўм)</label>
    <input class="fld" id="exp_sum" type="number" />
    <label class="fl">Нимага (изоҳ)</label>
    <input class="fld" id="exp_note" placeholder="Масалан: клей олинди" />
    <div class="flx" style="gap:10px;margin-top:16px;">
        <button class="btn ghost" style="flex:1" onclick="closeModal()">${t('cancel') || 'Bekor qilish'}</button>
        <button class="btn primary" style="flex:1" onclick="expSave(this)">${t('save') || 'Saqlash'}</button>
    </div>
    `);
};

window.expSave = async (btn) => {
    let data = {
        kind: "Xarajat",
        amount: parseFloat(_id('exp_sum').value) || 0,
        note: _id('exp_note').value.trim(),
        firm: window.FIRM || ""
    };
    if(data.amount <= 0) return toast("Summa 0 dan katta bo'lishi kerak", "err");
    if(!data.note) return toast("Изоҳ yozilishi shart", "err");

    if(btn){btn.disabled=true;btn.textContent='…';}   // такрор босилмасин
    let res = await api('/api/hr/cash', 'POST', data);
    if(res) {
        toast("Сақланди");
        closeModal();
        await expLoad();
    } else if(btn){btn.disabled=false;btn.textContent=t('save')||'Saqlash';}
};
