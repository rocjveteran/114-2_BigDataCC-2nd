<?php
// ui.php - shared UI helpers (simple & editable)
if (session_status() === PHP_SESSION_NONE) session_start();

function h($s){ return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function role_name($r){
  if ($r==='boss') return '老闆';
  if ($r==='admin') return '管理員';
  return '員工';
}

function is_boss(){
  return (($_SESSION['role'] ?? '') === 'boss');
}

function is_admin(){
  $r = ($_SESSION['role'] ?? '');
  return in_array($r, ['admin','boss'], true);
}

function can_manage_user($target_role, $target_id){
  $my_role = ($_SESSION['role'] ?? '');
  $my_id   = (int)($_SESSION['user_id'] ?? 0);

  if ($my_role === 'boss') return true; // boss can manage anyone (including self)
  if ($my_role === 'admin') {
    if ($target_id === $my_id) return false; // admin cannot manage self
    return ($target_role === 'employee');    // admin can manage employees only
  }
  return false; // employee
}

function badge($txt, $type){
  $type = in_array($type, ['ok','warn','off','bad','info'], true) ? $type : 'off';
  return '<span class="badge '.$type.'">'.h($txt).'</span>';
}

function icon_svg($name){
  $c = 'currentColor';
  $s = '<svg class="ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="'.$c.'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">';
  if ($name === 'shield')   return $s.'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
  if ($name === 'lock')     return $s.'<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';
  if ($name === 'ship')     return $s.'<path d="M20 21H4"/><path d="M4 21l2-6h12l2 6"/><path d="M6 15V9l6-3 6 3v6"/><path d="M12 6V3"/><path d="M12 9v6"/></svg>';
  if ($name === 'login')    return $s.'<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/></svg>';
  if ($name === 'logout')   return $s.'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>';
  if ($name === 'clock')    return $s.'<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>';
  if ($name === 'list')     return $s.'<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>';
  if ($name === 'users')    return $s.'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
  if ($name === 'plus')     return $s.'<path d="M12 5v14"/><path d="M5 12h14"/></svg>';
  if ($name === 'edit')     return $s.'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>';
  if ($name === 'trash')    return $s.'<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
  if ($name === 'download') return $s.'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>';
  if ($name === 'plane')    return $s.'<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>';
  if ($name === 'check')    return $s.'<path d="M20 6L9 17l-5-5"/></svg>';
  if ($name === 'x')        return $s.'<path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>';
  return '';
}

function style_link(){
  $p = __DIR__ . '/style.css';
  $v = @filemtime($p) ?: time();
  echo '<link rel="stylesheet" href="style.css?v='.$v.'">';
}

function page_footer(){
  $y = date('Y');
  echo '<footer class="site-footer"><div class="wrap"><div class="footer-row">';
  echo '<div class="footer-brand">';
  echo '<span class="footer-logo">'.icon_svg('ship').'</span>';
  echo '<span>海事勤務值勤管理系統</span>';
  echo '</div>';
  echo '<div class="footer-meta">114-2 巨量資料與雲端運算 · 第 2 組 · &copy; '.$y.'</div>';
  echo '</div></div></footer>';
}

function page_header($title, $subtitle = '', $eyebrow = '', $actions_html = ''){
  echo '<header class="page-header">';
  echo '<div class="ph-text">';
  if ($eyebrow !== '') echo '<div class="eyebrow">'.h($eyebrow).'</div>';
  echo '<h1 class="page-title">'.h($title).'</h1>';
  if ($subtitle !== '') echo '<p class="page-subtitle">'.h($subtitle).'</p>';
  echo '</div>';
  if ($actions_html !== '') echo '<div class="ph-actions">'.$actions_html.'</div>';
  echo '</header>';
}

function nav_link($href, $label, $current = false){
  $cls = 'nav-link' . ($current ? ' active' : '');
  return '<a class="'.$cls.'" href="'.h($href).'">'.h($label).'</a>';
}

function nav_top($title = ''){
  $name = $_SESSION['full_name'] ?? '';
  $role = $_SESSION['role'] ?? '';
  $cur  = basename($_SERVER['SCRIPT_NAME'] ?? '');

  echo '<header class="top"><div class="wrap nav-wrap"><div class="nav">';

  echo '<a class="brand" href="'.(isset($_SESSION['user_id']) ? 'punch.php' : 'login.php').'">';
  echo '<span class="logo">'.icon_svg('ship').'</span>';
  echo '<span class="brand-name">海事勤務</span>';
  echo '<span class="brand-tag">值勤管理系統</span>';
  echo '</a>';

  if (isset($_SESSION['user_id'])) {
    echo '<nav class="nav-links">';
    echo nav_link('punch.php',   '值勤',   $cur==='punch.php');
    echo nav_link('records.php', '我的紀錄', $cur==='records.php');
    echo nav_link('leave.php',   '請假',   in_array($cur, ['leave.php'], true));
    if (is_admin()) {
      echo '<span class="nav-sep"></span>';
      echo nav_link('admin_status.php',    '勤務總覽', in_array($cur, ['admin_status.php','admin_edit.php'], true));
      echo nav_link('admin_leave.php',     '請假審核', $cur==='admin_leave.php');
      echo nav_link('admin_users.php',     '帳號管理', in_array($cur, ['admin_users.php','admin_create_user.php','admin_user_edit.php'], true));
      echo nav_link('admin_dashboard.php', '分析儀表板', $cur==='admin_dashboard.php');
    }
    echo '</nav>';
  }

  echo '<span class="sp"></span>';

  echo '<div class="nav-right">';
  if (isset($_SESSION['user_id'])) {
    if ($name) {
      echo '<span class="user-chip">';
      echo '<span class="user-name">'.h($name).'</span>';
      echo '<span class="user-role">'.h(role_name($role)).'</span>';
      echo '</span>';
    }
    echo '<a class="btn small ghost-on-dark" href="logout.php">'.icon_svg('logout').'登出</a>';
  } else {
    echo '<a class="btn small primary" href="login.php">'.icon_svg('login').'登入</a>';
  }
  echo '</div>';

  echo '</div></div></header>';
}
