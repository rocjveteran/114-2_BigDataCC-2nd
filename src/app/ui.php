<?php
// ui.php - shared UI helpers
// ── Session hardening (must run before session_start) ──
if (session_status() === PHP_SESSION_NONE) {
  ini_set('session.use_strict_mode', '1');
  ini_set('session.cookie_httponly', '1');
  $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
         || ($_SERVER['SERVER_PORT'] ?? '') == 443;
  session_set_cookie_params([
    'lifetime' => 0,
    'path'     => '/',
    'domain'   => '',
    'secure'   => $secure,
    'httponly' => true,
    'samesite' => 'Lax',
  ]);
  session_start();
}
require_once __DIR__ . '/csrf.php';

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

  if ($my_role === 'boss') return true;
  if ($my_role === 'admin') {
    if ($target_id === $my_id) return false;
    return ($target_role === 'employee');
  }
  return false;
}

function badge($txt, $type){
  $type = in_array($type, ['ok','warn','off','bad','info'], true) ? $type : 'off';
  return '<span class="badge '.$type.'">'.h($txt).'</span>';
}

function avatar_initial($name, $size = 32, $variant = 'muted'){
  $init = $name ? mb_substr($name, 0, 1) : '·';
  $sz = in_array($size, [32,44,56], true) ? $size : 32;
  return '<span class="avatar sz-'.$sz.' '.h($variant).'">'.h($init).'</span>';
}

function icon_svg($name){
  $c = 'currentColor';
  $s = '<svg class="ico" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="'.$c.'" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">';
  switch ($name) {
    case 'shield':    return $s.'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
    case 'lock':      return $s.'<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';
    case 'ship':      return $s.'<path d="M20 21H4"/><path d="M4 21l2-6h12l2 6"/><path d="M6 15V9l6-3 6 3v6"/><path d="M12 6V3"/><path d="M12 9v6"/></svg>';
    case 'login':     return $s.'<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/></svg>';
    case 'logout':    return $s.'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>';
    case 'clock':     return $s.'<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></svg>';
    case 'list':      return $s.'<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>';
    case 'users':     return $s.'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
    case 'plus':      return $s.'<path d="M12 5v14"/><path d="M5 12h14"/></svg>';
    case 'edit':      return $s.'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>';
    case 'trash':     return $s.'<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>';
    case 'download':  return $s.'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>';
    case 'plane':     return $s.'<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg>';
    case 'check':     return $s.'<path d="M20 6L9 17l-5-5"/></svg>';
    case 'x':         return $s.'<path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>';
    case 'home':      return $s.'<path d="M3 12L12 4l9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>';
    case 'compass':   return $s.'<circle cx="12" cy="12" r="9"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>';
    case 'anchor':    return $s.'<circle cx="12" cy="5" r="3"/><path d="M12 8v13"/><path d="M5 12H2a10 10 0 0 0 20 0h-3"/></svg>';
    case 'chart':     return $s.'<path d="M3 3v18h18"/><path d="M7 14l4-4 4 3 5-7"/></svg>';
    case 'user':      return $s.'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
    case 'calendar':  return $s.'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/></svg>';
    case 'menu':      return $s.'<path d="M3 6h18"/><path d="M3 12h18"/><path d="M3 18h18"/></svg>';
    case 'settings':  return $s.'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
    case 'briefcase': return $s.'<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>';
    case 'wave':      return $s.'<path d="M2 12c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/><path d="M2 18c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/></svg>';
  }
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

function sb_item($href, $icon, $label, $active = false){
  $cls = 'sb-item' . ($active ? ' active' : '');
  return '<a class="'.$cls.'" href="'.h($href).'">'.icon_svg($icon).'<span>'.h($label).'</span></a>';
}

function nav_top($title = ''){
  $name = $_SESSION['full_name'] ?? '';
  $role = $_SESSION['role'] ?? '';
  $cur  = basename($_SERVER['SCRIPT_NAME'] ?? '');
  $logged_in = isset($_SESSION['user_id']);

  if (!$logged_in) {
    echo '<header class="top"><div class="wrap nav-wrap"><div class="nav">';
    echo '<a class="brand" href="login.php">';
    echo '<span class="logo">'.icon_svg('ship').'</span>';
    echo '<span class="brand-name">海事勤務</span>';
    echo '<span class="brand-tag">值勤管理系統</span>';
    echo '</a>';
    echo '<span class="sp"></span>';
    echo '<div class="nav-right"><a class="btn small primary" href="login.php">'.icon_svg('login').'登入</a></div>';
    echo '</div></div></header>';
    return;
  }

  // Mobile top bar (hamburger)
  echo '<div class="sb-mobile">';
  echo '<button class="sb-burger" onclick="document.body.classList.toggle(\'sb-open\')" aria-label="切換選單">'.icon_svg('menu').'</button>';
  echo '<span class="sb-mbrand"><span class="sb-mlogo">'.icon_svg('ship').'</span>海事勤務</span>';
  echo '</div>';

  // Sidebar
  echo '<aside class="sidebar">';
  echo '<a class="sb-brand" href="dashboard.php">';
  echo '<span class="sb-logo">'.icon_svg('ship').'</span>';
  echo '<span class="sb-bcol"><span class="sb-bname">海事勤務</span><span class="sb-btag">值勤管理系統</span></span>';
  echo '</a>';

  echo '<nav class="sb-nav">';

  // Group: 個人 (personal)
  echo '<div class="sb-group">';
  echo '<div class="sb-group-label">個人</div>';
  echo sb_item('dashboard.php', 'home',     '儀表板',  $cur==='dashboard.php');
  echo sb_item('punch.php',     'clock',    '值勤打卡', $cur==='punch.php');
  echo sb_item('records.php',   'list',     '我的紀錄', $cur==='records.php');
  echo sb_item('leave.php',     'plane',    '請假',    $cur==='leave.php');
  echo sb_item('profile.php',   'user',     '個人檔案', $cur==='profile.php');
  echo '</div>';

  // Group: 艦務 (fleet)
  echo '<div class="sb-group">';
  echo '<div class="sb-group-label">艦務</div>';
  echo sb_item('crew.php',     'users',   '艦上人員', $cur==='crew.php');
  echo sb_item('voyages.php',  'compass', '航次紀錄', $cur==='voyages.php');
  echo '</div>';

  if (is_admin()) {
    echo '<div class="sb-group">';
    echo '<div class="sb-group-label">管理</div>';
    echo sb_item('admin_status.php',    'shield',    '勤務總覽', in_array($cur, ['admin_status.php','admin_edit.php'], true));
    echo sb_item('admin_leave.php',     'briefcase', '請假審核', $cur==='admin_leave.php');
    echo sb_item('admin_users.php',     'users',     '帳號管理', in_array($cur, ['admin_users.php','admin_create_user.php','admin_user_edit.php'], true));
    echo sb_item('admin_dashboard.php', 'chart',     '分析儀表板', $cur==='admin_dashboard.php');
    echo '</div>';
  }

  echo '</nav>';

  // Footer
  echo '<div class="sb-foot">';
  echo avatar_initial($name, 32, 'primary');
  echo '<span class="sb-user"><span class="sb-uname">'.h($name).'</span><span class="sb-urole">'.h(role_name($role)).'</span></span>';
  // Logout via POST + CSRF token (so it can't be triggered by GET / <img>)
  echo '<form method="post" action="logout.php" style="display:inline;margin:0;padding:0;">';
  echo csrf_input();
  echo '<button class="sb-logout" type="submit" title="登出" aria-label="登出">'.icon_svg('logout').'</button>';
  echo '</form>';
  echo '</div>';
  echo '</aside>';
}
