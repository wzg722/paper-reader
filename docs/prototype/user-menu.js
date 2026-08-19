/* ============================================================
   右上角用户菜单（全站共享）— 依赖 data.js 的 PM.getUser/logout
   页面需包含:
   <div class="user-menu">
     <div class="avatar" id="avatarBtn">客</div>
     <div class="um-drop hidden" id="userDrop">
       <div class="um-head"><b id="umName">—</b><span id="umEmail"></span></div>
       <a href="profile.html" data-i18n="menu_profile">👤 个人中心</a>
       <a href="profile.html#edit" data-i18n="menu_edit">📝 修改资料</a>
       <div class="um-sep"></div>
       <a href="javascript:logout()" data-i18n="menu_logout">🚪 退出登录</a>
     </div>
   </div>
   ============================================================ */
(function(){
  var btn = document.getElementById('avatarBtn');
  var menu = document.getElementById('userDrop');
  if(!btn || !menu) return;
  var u = PM.getUser();
  var av = u.avatar || PM.defaultAvatar;
  if(/^data:image/.test(av)){
    btn.textContent = '';
    var img = document.createElement('img');
    img.src = av;
    img.style.cssText = 'width:100%;height:100%;border-radius:50%;object-fit:cover;display:block';
    btn.appendChild(img);
  } else {
    btn.textContent = av.length <= 2 ? av : (u.name ? u.name[0] : '客');
  }
  btn.title = u.name + '（点击打开菜单）';
  var nm = document.getElementById('umName');
  var em = document.getElementById('umEmail');
  if(nm) nm.textContent = u.name;
  if(em) em.textContent = u.email || (u.role || '');
  btn.addEventListener('click', function(e){
    e.stopPropagation();
    menu.classList.toggle('hidden');
  });
  document.addEventListener('click', function(){ menu.classList.add('hidden') });
  PM.applyI18n();   /* 英文模式：替换所有 [data-i18n] 文案 */
})();
function logout(){
  PM.logout();
  location.href = 'login.html';
}
