/* ================= Start ================= */
/* Tokeni bor foydalanuvchi lendingni ham, login oynasini ham ko'rmaydi —
   to'g'ri tizimga o'tadi. Token yaroqsiz bo'lsa `logout()` sahifani
   qayta yuklaydi va lending ochiladi. */
if(TOKEN&&ME){
  fetch(API+'/api/auth/me',{headers:{'Authorization':'Bearer '+TOKEN}})
    .then(r=>r.ok?enterApp():logout()).catch(()=>{ lendingBoshla(); });
}else{
  lendingBoshla();
}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
