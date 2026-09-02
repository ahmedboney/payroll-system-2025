function toggleSidebar(){
    document.getElementById('sidebar').classList.toggle('open');
}
function openModal(id){ document.getElementById(id).classList.add('active'); }
function closeModal(id){ document.getElementById(id).classList.remove('active'); }
document.addEventListener('click', function(e){
    if(e.target.classList.contains('modal-overlay')) e.target.classList.remove('active');
});
document.addEventListener('keydown',function(e){
    if(e.key==='Escape'){
        document.querySelectorAll('.modal-overlay.active').forEach(function(m){m.classList.remove('active');});
    }
});
function fmt(n){ return (n||0).toLocaleString('en-US',{maximumFractionDigits:2}); }
function esc(s){ return (s||'').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }

// ===== Theme (Dark Mode) =====
function applyTheme(mode){
    var t=document.getElementById('themeToggle');
    if(mode==='dark'){
        document.body.classList.add('dark-mode');
        if(t) t.textContent='☀️';
        if(t) t.title='التبديل للوضع النهاري';
    }else{
        document.body.classList.remove('dark-mode');
        if(t) t.textContent='🌙';
        if(t) t.title='التبديل للوضع الليلي';
    }
    try{ localStorage.setItem('payroll_theme', mode); }catch(e){}
}
function toggleTheme(){
    var cur=document.body.classList.contains('dark-mode')?'light':'dark';
    applyTheme(cur);
}
(function(){
    var saved='light';
    try{ saved=localStorage.getItem('payroll_theme')||'light'; }catch(e){}
    // respect OS preference if never chosen
    try{
        if(!localStorage.getItem('payroll_theme') && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches){
            saved='dark';
        }
    }catch(e){}
    applyTheme(saved);
})();
