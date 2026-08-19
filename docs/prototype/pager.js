/* ============================================================
   分页组件 v1 — PaperMind 研读
   用法:
     renderPager({
       el: 容器元素, page: 当前页, pageSize: 每页条数, total: 总条数,
       onChange: function(newPage){ 重新渲染列表 },
       onSizeChange: function(newSize){ 重置到第1页并重新渲染 }
     })
   特性: 页码折叠(首尾+当前±2)、上/下/首/末页、每页条数 5/10/20/50、
         跳页输入、范围信息("共 N 条 · 第 x/y 页")、边界禁用
   配套 CSS 见 style.css 的 .pager 系列
   ============================================================ */
function renderPager(opt){
  var el = opt.el;
  var page = Math.max(1, opt.page);
  var size = opt.pageSize;
  var total = Math.max(0, opt.total);
  var pages = Math.max(1, Math.ceil(total / size));
  if(page > pages) page = pages;

  var html = '<div class="pager">';
  html += '<span class="pager-info">'+PM.t('pager_total')+'<b>' + total + '</b>'+PM.t('pager_pages')+'<b>' + page + '/' + pages + '</b></span>';

  html += '<div class="pager-btns">';
  html += '<button class="pager-btn" data-p="1"'   + (page<=1   ? ' disabled':'') + ' title="首页">«</button>';
  html += '<button class="pager-btn" data-p="'+(page-1)+'"' + (page<=1 ? ' disabled':'') + ' title="上一页">‹</button>';
  pageNums(page, pages).forEach(function(n){
    if(n === '...') html += '<span class="pager-dots">…</span>';
    else html += '<button class="pager-btn' + (n===page ? ' active':'') + '" data-p="' + n + '">' + n + '</button>';
  });
  html += '<button class="pager-btn" data-p="'+(page+1)+'"' + (page>=pages ? ' disabled':'') + ' title="下一页">›</button>';
  html += '<button class="pager-btn" data-p="'+pages+'"' + (page>=pages ? ' disabled':'') + ' title="末页">»</button>';
  html += '</div>';

  html += '<label class="pager-size">'+PM.t('pager_per')+' <select>';
  [5,10,20,50].forEach(function(s){
    html += '<option value="'+s+'"' + (s===size ? ' selected':'') + '>'+s+'</option>';
  });
  html += '</select>'+PM.t('pager_per_unit')+'</label>';
  html += '</div>';   /* /pager */
  el.innerHTML = html;

  /* 绑定事件 */
  el.querySelectorAll('.pager-btn:not([disabled])').forEach(function(b){
    b.onclick = function(){ opt.onChange(parseInt(b.dataset.p,10)); };
  });
  el.querySelector('.pager-size select').onchange = function(){
    opt.onSizeChange(parseInt(this.value,10));
  };
}

/* 页码折叠算法：始终含 1 与末页，当前页前后各 2 页，间隔用 … 表示 */
function pageNums(cur, pages){
  var set = {1:1, [pages]:pages};
  for(var i = Math.max(1, cur-2); i <= Math.min(pages, cur+2); i++) set[i] = i;
  var keys = Object.keys(set).map(Number).sort(function(a,b){ return a-b; });
  var out = [], prev = 0;
  keys.forEach(function(k){
    if(prev && k - prev > 1) out.push('...');
    out.push(k); prev = k;
  });
  return out;
}
