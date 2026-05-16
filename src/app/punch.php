<?php
require 'auth.php';
require 'db.php';
require 'ui.php';

date_default_timezone_set('Asia/Taipei');

$uid = (int)$_SESSION['user_id'];
$d   = date('Y-m-d');
$now = date('Y-m-d H:i:s');

$msg = null;

$stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
$stmt->execute([$uid, $d]);
$a = $stmt->fetch();

// leave check (approved)
$stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
$stmt->execute([$uid, $d, $d]);
$lv = $stmt->fetchColumn();


if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $act = $_POST['act'] ?? '';

  $pdo->beginTransaction();
  try {
    if ($act === 'set_cond' && is_admin()) {
      $valid_zones = ['港口','近海','外海'];
      $valid_seas  = ['平靜','輕浪','中浪','大浪'];
      $z = $_POST['duty_zone'] ?? '';
      $s = $_POST['sea_state'] ?? '';
      $z = in_array($z, $valid_zones, true) ? $z : null;
      $s = in_array($s, $valid_seas,  true) ? $s : null;
      $upd = $pdo->prepare("UPDATE attendance SET duty_zone=?, sea_state=? WHERE work_date=?");
      $upd->execute([$z, $s, $d]);
      $aff = $upd->rowCount();
      $_SESSION['today_zone'] = $z;
      $_SESSION['today_sea']  = $s;
      $msg = $aff>0 ? "已套用今日海域/海象至 {$aff} 筆紀錄" : "今日尚無人值勤，海象條件已暫存，待人員打卡後將自動套用";
    } else {
      $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? FOR UPDATE");
      $stmt->execute([$uid, $d]);
      $row = $stmt->fetch();

      $today_zone = null; $today_sea = null;
      $look = $pdo->prepare("SELECT duty_zone, sea_state FROM attendance WHERE work_date=? AND (duty_zone IS NOT NULL OR sea_state IS NOT NULL) LIMIT 1");
      $look->execute([$d]);
      if ($r = $look->fetch()) { $today_zone = $r['duty_zone']; $today_sea = $r['sea_state']; }
      if (!$today_zone) $today_zone = $_SESSION['today_zone'] ?? null;
      if (!$today_sea)  $today_sea  = $_SESSION['today_sea']  ?? null;

      if ($act === 'in') {
        if (!$row) {
          $ins = $pdo->prepare("INSERT INTO attendance(user_id, work_date, check_in, status, duty_zone, sea_state) VALUES(?,?,?,'open',?,?)");
          $ins->execute([$uid, $d, $now, $today_zone, $today_sea]);
          $msg = "值勤開始：{$now}";
        } else if (empty($row['check_in'])) {
          $upd = $pdo->prepare("UPDATE attendance SET check_in=?, status='open', duty_zone=COALESCE(duty_zone,?), sea_state=COALESCE(sea_state,?) WHERE att_id=?");
          $upd->execute([$now, $today_zone, $today_sea, (int)$row['att_id']]);
          $msg = "值勤開始：{$now}";
        } else {
          $msg = "已值勤開始，不能重複。";
        }
      } elseif ($act === 'out') {
        if (!$row || empty($row['check_in'])) {
          $msg = "尚未值勤開始，不能結束。";
        } else if (!empty($row['check_out'])) {
          $msg = "已值勤結束，不能重複。";
        } else {
          $upd = $pdo->prepare("UPDATE attendance SET check_out=?, status='done' WHERE att_id=?");
          $upd->execute([$now, (int)$row['att_id']]);
          $msg = "值勤結束：{$now}";
        }
      }
    }

    $pdo->commit();
  } catch (Exception $e) {
    $pdo->rollBack();
    $msg = "操作失敗（請重試）";
  }

  $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? LIMIT 1");
  $stmt->execute([$uid, $d]);
  $a = $stmt->fetch();

  $stmt = $pdo->prepare("SELECT leave_type FROM leaves WHERE user_id=? AND status='approved' AND date_from<=? AND date_to>=? LIMIT 1");
  $stmt->execute([$uid, $d, $d]);
  $lv = $stmt->fetchColumn();
}

$in  = $a['check_in'] ?? null;
$out = $a['check_out'] ?? null;

$can_in  = empty($in) && !$lv;
$can_out = (!empty($in) && empty($out)) && !$lv;

$weekday_zh = ['日','一','二','三','四','五','六'];
$wd = $weekday_zh[(int)date('w')];
?>
<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>值勤 · 海事勤務</title>
  <?php style_link(); ?>
</head>
<body>
  <?php nav_top(); ?>
  <div class="wrap mid">
    <?php page_header(
      '今日值勤',
      $d.' · 星期'.$wd.'。請依勤務開始與結束時間打卡，結束後資料即進入「我的紀錄」。',
      'TODAY · 今日'
    ); ?>

    <?php if(!empty($lv)): ?>
      <div class="msg" style="background:rgba(42,90,153,.06);border-color:rgba(42,90,153,.22);color:var(--info)">
        <strong>今日已核准請假</strong> — 請假期間內不需打卡。
      </div>
    <?php endif; ?>

    <?php if($msg): ?>
      <?php
        $cls = '';
        if (str_contains($msg,'開始：') || str_contains($msg,'結束：')) $cls = 'ok';
        elseif (str_contains($msg,'不能') || str_contains($msg,'失敗') || str_contains($msg,'尚未')) $cls = 'err';
      ?>
      <p class="msg <?= $cls ?>"><?= h($msg) ?></p>
    <?php endif; ?>

    <div class="grid2">
      <div class="card">
        <div class="card-head">
          <h2>值勤開始</h2>
          <?php if(!empty($in)): ?><span class="badge ok">已打卡</span><?php else: ?><span class="badge off">尚未開始</span><?php endif; ?>
        </div>
        <div class="t serif"><?= h($in ?? '—') ?></div>
        <form method="post" style="margin-top:8px;">
          <input type="hidden" name="act" value="in">
          <button class="btn primary" type="submit" style="width:100%;" <?= $can_in ? '' : 'disabled' ?>>
            <?= icon_svg('clock') ?>開始值勤
          </button>
        </form>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>值勤結束</h2>
          <?php if(!empty($out)): ?><span class="badge ok">已結束</span><?php elseif(!empty($in)): ?><span class="badge warn">值勤中</span><?php else: ?><span class="badge off">尚未開始</span><?php endif; ?>
        </div>
        <div class="t serif"><?= h($out ?? '—') ?></div>
        <form method="post" style="margin-top:8px;">
          <input type="hidden" name="act" value="out">
          <button class="btn primary" type="submit" style="width:100%;" <?= $can_out ? '' : 'disabled' ?>>
            <?= icon_svg('check') ?>結束值勤
          </button>
        </form>
      </div>
    </div>

    <?php
    // ── Ship-wide conditions today (mode across non-null rows) ──
    $today_zone = null; $today_sea = null;
    $st = $pdo->prepare("SELECT duty_zone, COUNT(*) c FROM attendance WHERE work_date=? AND duty_zone IS NOT NULL GROUP BY duty_zone ORDER BY c DESC LIMIT 1");
    $st->execute([$d]);
    if ($r = $st->fetch()) $today_zone = $r['duty_zone'];
    $st = $pdo->prepare("SELECT sea_state, COUNT(*) c FROM attendance WHERE work_date=? AND sea_state IS NOT NULL GROUP BY sea_state ORDER BY c DESC LIMIT 1");
    $st->execute([$d]);
    if ($r = $st->fetch()) $today_sea = $r['sea_state'];
    if (!$today_zone) $today_zone = $_SESSION['today_zone'] ?? null;
    if (!$today_sea)  $today_sea  = $_SESSION['today_sea']  ?? null;

    $zone_cls_map = ['港口'=>'zone-port','近海'=>'zone-near','外海'=>'zone-far'];
    $sea_cls_map  = ['平靜'=>'sea-calm','輕浪'=>'sea-light','中浪'=>'sea-med','大浪'=>'sea-rough'];
    $sea_amp_map  = ['平靜'=>1.5,'輕浪'=>3.5,'中浪'=>7.0,'大浪'=>11.0];
    $sea_anim_map = ['平靜'=>'calm','輕浪'=>'light','中浪'=>'med','大浪'=>'rough'];
    $sea_amp  = $sea_amp_map[$today_sea]  ?? 2.0;       // default subtle motion
    $sea_anim = $sea_anim_map[$today_sea] ?? 'calm';

    // Build a wavy SVG path: starts at -80, repeats wavelength=40 across viewBox
    function wave_path($baseline, $amp, $wl=40, $x0=-80, $x1=760){
      $half = $wl/2; $a = -$amp;
      $d = "M {$x0} {$baseline} q {$half} {$a} {$wl} 0";
      $x = $x0 + $wl;
      while ($x < $x1) { $d .= " t {$wl} 0"; $x += $wl; }
      return $d;
    }

    // ── Ship crew visualization ─────────────────────────────
    $stmt = $pdo->prepare("
      SELECT u.user_id, u.full_name, u.duty_position,
             a.check_in, a.check_out,
             (SELECT leave_type FROM leaves lv
              WHERE lv.user_id=u.user_id AND lv.status='approved'
                AND lv.date_from<=? AND lv.date_to>=? LIMIT 1) AS leave_type
      FROM users u
      LEFT JOIN attendance a ON a.user_id=u.user_id AND a.work_date=?
      WHERE u.is_active=1
      ORDER BY u.user_id
    ");
    $stmt->execute([$d, $d, $d]);
    $crew_all = $stmt->fetchAll();

    $pos_groups = [];
    foreach ($crew_all as $cr) {
      $pos = $cr['duty_position'] ?: '前甲板';
      if ($cr['leave_type'])                                      $st = 'leave';
      elseif (!empty($cr['check_in']) && empty($cr['check_out'])) $st = 'on';
      elseif (!empty($cr['check_out']))                           $st = 'done';
      else                                                        $st = 'off';
      $pos_groups[$pos][] = [
        'name'  => $cr['full_name'],
        'uid'   => (int)$cr['user_id'],
        'status'=> $st,
        'is_me' => ((int)$cr['user_id'] === $uid),
      ];
    }

    // Coords for Anping-class side profile (canvas 900 x 360)
    // Hull line at y=215; superstructure y=160-215; bridge y=105-160; mast y=40-105; waves y=340+
    $pos_coords = [
      '瞭望台' => ['cx'=>420, 'cy'=>60,  'cap'=>['x'=>500, 'y'=>62,  'leader'=>true, 'ta'=>'start' ]],
      '艦橋'   => ['cx'=>430, 'cy'=>130, 'cap'=>['x'=>430, 'y'=>95,  'ta'=>'middle']],
      '通訊室' => ['cx'=>300, 'cy'=>185, 'cap'=>['x'=>300, 'y'=>328, 'leader'=>true, 'ta'=>'middle']],
      '前甲板' => ['cx'=>130, 'cy'=>195, 'cap'=>['x'=>130, 'y'=>328, 'leader'=>true, 'ta'=>'middle']],
      '後甲板' => ['cx'=>700, 'cy'=>195, 'cap'=>['x'=>700, 'y'=>328, 'leader'=>true, 'ta'=>'middle']],
      '機艙'   => ['cx'=>520, 'cy'=>262, 'cap'=>['x'=>520, 'y'=>328, 'leader'=>true, 'ta'=>'middle']],
    ];
    $st_zh_map = ['on'=>'值勤中','done'=>'已結束','leave'=>'請假','off'=>'未值勤'];

    // Compute crew dot position. Max 3 per row, rows 28px apart, cols 36px apart.
    function dot_pos($i, $n, $cx, $cy){
      $per_row = min($n, 3);
      $rows = (int)ceil($n / $per_row);
      $row = (int)floor($i / $per_row);
      $col = $i % $per_row;
      $items_this_row = ($row === $rows - 1) ? ($n - $row * $per_row) : $per_row;
      $offset_x = ($col - ($items_this_row - 1) / 2.0) * 36;
      $offset_y = ($row - ($rows - 1) / 2.0) * 28;
      return [$cx + $offset_x, $cy + $offset_y];
    }
    ?>

    <div class="card ship-card">
      <div class="card-head">
        <h2>今日艦上人員配置</h2>
        <div class="ship-conditions">
          <?php if ($today_zone): ?>
            <span class="cond-chip <?= h($zone_cls_map[$today_zone] ?? '') ?>"><span class="cond-k">海域</span><?= h($today_zone) ?></span>
          <?php else: ?>
            <span class="cond-chip unset"><span class="cond-k">海域</span>未設定</span>
          <?php endif; ?>
          <?php if ($today_sea): ?>
            <span class="cond-chip <?= h($sea_cls_map[$today_sea] ?? '') ?>"><span class="cond-k">海象</span><?= h($today_sea) ?></span>
          <?php else: ?>
            <span class="cond-chip unset"><span class="cond-k">海象</span>未設定</span>
          <?php endif; ?>
          <span class="muted" style="font-size:12.5px;margin-left:6px;"><?= h($d) ?> · 星期<?= h($wd) ?></span>
        </div>
      </div>
      <svg class="ship-svg" viewBox="0 0 900 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="海巡署安平級巡防艦人員配置示意圖">
        <!-- ═══════════════════════════════════════════════════════════════
             安平級巡防艦 (Anping-class OPV, 600t)
             Wave-piercing catamaran, angular stealth profile
             ═══════════════════════════════════════════════════════════════ -->

        <!-- Hull — sharp wave-piercing bow, flat bottom, vertical stern -->
        <path class="sh-hull" d="
          M 60,300
          L 50,275
          L 90,245
          L 170,215
          L 820,215
          L 840,232
          L 840,300
          Z"/>
        <!-- Hull diagonal stripe (海巡 identification, RAL primary subtle) -->
        <path class="sh-stripe" d="M 100,295 L 820,250 L 820,265 L 110,300 Z"/>
        <!-- Bow registration text -->
        <text class="sh-reg" x="125" y="270" text-anchor="start">CG-601</text>

        <!-- Lower superstructure (comms/cabin tier) -->
        <path class="sh-struct" d="M 200,215 L 215,165 L 615,165 L 630,215 Z"/>
        <!-- Upper bridge tier (raised, narrower, with forward-raked front) -->
        <path class="sh-struct" d="M 285,165 L 305,108 L 555,108 L 575,165 Z"/>
        <!-- Bridge front raked window band (sloped to follow front edge) -->
        <path class="sh-window" d="M 308,115 L 322,128 L 538,128 L 552,115 Z"/>
        <!-- Bridge side window strip (long horizontal slot) -->
        <rect class="sh-window" x="340" y="140" width="180" height="9" rx="1"/>
        <!-- Wing platform (port bridge wing extension) -->
        <line class="sh-railing" x1="262" y1="160" x2="285" y2="160"/>
        <line class="sh-railing" x1="575" y1="160" x2="598" y2="160"/>

        <!-- Mast assembly (single integrated mast with radar dome) -->
        <line class="sh-mast" x1="420" y1="108" x2="420" y2="32"/>
        <!-- Mast struts (tripod-like) -->
        <line class="sh-mast-thin" x1="420" y1="108" x2="400" y2="80"/>
        <line class="sh-mast-thin" x1="420" y1="108" x2="440" y2="80"/>
        <!-- Lower antenna platform -->
        <rect class="sh-platform" x="402" y="92" width="36" height="4" rx="1"/>
        <!-- Radar dome (signature feature of Anping) -->
        <circle class="sh-dome" cx="420" cy="78" r="11"/>
        <!-- Upper antenna platform / sensor mount -->
        <line class="sh-mast" x1="397" y1="55" x2="443" y2="55"/>
        <line class="sh-mast-thin" x1="403" y1="55" x2="403" y2="46"/>
        <line class="sh-mast-thin" x1="437" y1="55" x2="437" y2="46"/>
        <!-- Top antenna -->
        <line class="sh-mast-thin" x1="420" y1="32" x2="420" y2="20"/>
        <circle cx="420" cy="20" r="2" fill="var(--muted)" opacity=".5"/>
        <!-- Signal flag halyards (dashed lines from mast to bow/stern, decorative) -->
        <line class="sh-halyard" x1="420" y1="50" x2="170" y2="215"/>
        <line class="sh-halyard" x1="420" y1="50" x2="700" y2="215"/>

        <!-- Funnel (integrated, aft of bridge, low profile for stealth) -->
        <path class="sh-funnel" d="M 590,165 L 595,138 L 615,138 L 620,165 Z"/>

        <!-- Foredeck weapon — NCSIST 2.75in rocket launcher pedestal -->
        <rect class="sh-weapon" x="142" y="208" width="22" height="10" rx="1"/>
        <rect class="sh-weapon" x="146" y="200" width="14" height="10" rx="1"/>
        <line class="sh-mast-thin" x1="153" y1="200" x2="153" y2="194"/>

        <!-- Afterdeck weapon — 20mm autocannon -->
        <rect class="sh-weapon" x="745" y="208" width="18" height="10" rx="1"/>
        <line class="sh-mast-thin" x1="754" y1="208" x2="754" y2="198"/>

        <!-- Water cannon mount (above lower super, port side aft) -->
        <circle class="sh-weapon" cx="635" cy="180" r="4"/>
        <line class="sh-mast-thin" x1="635" y1="180" x2="660" y2="172"/>

        <!-- Catamaran twin hull hint (visible at stern through water) -->
        <line class="sh-water" x1="60" y1="305" x2="840" y2="305"/>
        <!-- Waterline -->
        <line class="sh-waterline" x1="40" y1="300" x2="860" y2="300"/>

        <!-- Sea waves (amplitude reflects today's sea state) -->
        <g class="sh-wave-group <?= h($sea_anim) ?>">
          <path class="sh-wave w1" d="<?= h(wave_path(335, $sea_amp,        40, -80, 980)) ?>"/>
          <?php if ($sea_amp >= 3): ?>
            <path class="sh-wave w2" d="<?= h(wave_path(348, $sea_amp * 0.78, 50, -80, 980)) ?>"/>
          <?php endif; ?>
          <?php if ($sea_amp >= 6): ?>
            <path class="sh-wave w3" d="<?= h(wave_path(358, $sea_amp * 0.58, 62, -80, 980)) ?>"/>
          <?php endif; ?>
        </g>

        <!-- Crew dots & station labels -->
        <?php foreach ($pos_coords as $pos_name => $c):
          $people = $pos_groups[$pos_name] ?? [];
          $n = count($people);
          $cap = $c['cap'];
        ?>
          <!-- Station label -->
          <text class="sh-pos-lbl" x="<?= $cap['x'] ?>" y="<?= $cap['y'] ?>" text-anchor="<?= $cap['ta'] ?>"><?= h($pos_name) ?> · <?= h($n) ?></text>
          <?php if (!empty($cap['leader'])):
            $dx = $cap['x'] - $c['cx'];
            $dy = $cap['y'] - $c['cy'];
            if (abs($dx) > abs($dy)) {
              // horizontal leader (e.g., 瞭望台)
              $lx1 = $c['cx'] + ($dx > 0 ?  14 : -14);
              $ly1 = $c['cy'];
              $lx2 = $cap['x'] + ($dx > 0 ? -4 :  4);
              $ly2 = $cap['y'];
            } else {
              // vertical leader (e.g., 通訊室, 機艙)
              $lx1 = $c['cx'];
              $ly1 = $c['cy'] + ($dy > 0 ?  14 : -14);
              $lx2 = $cap['x'];
              $ly2 = $cap['y'] + ($dy > 0 ? -12 : 12);
            }
          ?>
            <line class="sh-leader" x1="<?= $lx1 ?>" y1="<?= $ly1 ?>" x2="<?= $lx2 ?>" y2="<?= $ly2 ?>"/>
          <?php endif; ?>

          <?php if ($n === 0): ?>
            <circle class="sh-halo" cx="<?= $c['cx'] ?>" cy="<?= $c['cy'] ?>" r="13"/>
            <circle class="sh-dot off" cx="<?= $c['cx'] ?>" cy="<?= $c['cy'] ?>" r="11"/>
          <?php else: ?>
            <?php foreach ($people as $i => $person):
              [$cx, $cy] = dot_pos($i, $n, $c['cx'], $c['cy']);
              $st    = $person['status'];
              $me    = $person['is_me'] ? ' me' : '';
              $init  = mb_substr($person['name'], 0, 1);
              $tfill = ($st === 'on' || $st === 'done') ? '#fff' : 'var(--muted)';
              $st_zh = $st_zh_map[$st];
            ?>
              <g class="sh-crew-marker">
                <title><?= h($person['name']) ?> · <?= $st_zh ?></title>
                <circle class="sh-halo" cx="<?= round($cx, 1) ?>" cy="<?= round($cy, 1) ?>" r="14"/>
                <circle class="sh-dot <?= h($st.$me) ?>" cx="<?= round($cx, 1) ?>" cy="<?= round($cy, 1) ?>" r="12"/>
                <text class="sh-init" x="<?= round($cx, 1) ?>" y="<?= round($cy + 4, 1) ?>" text-anchor="middle" fill="<?= $tfill ?>"><?= h($init) ?></text>
              </g>
            <?php endforeach; ?>
          <?php endif; ?>
        <?php endforeach; ?>
      </svg>
      <div class="ship-legend">
        <span class="ship-legend-item"><span class="ship-legend-dot on"></span>值勤中</span>
        <span class="ship-legend-item"><span class="ship-legend-dot done"></span>已結束</span>
        <span class="ship-legend-item"><span class="ship-legend-dot leave"></span>請假</span>
        <span class="ship-legend-item"><span class="ship-legend-dot off"></span>未值勤</span>
        <span class="ship-legend-item ship-legend-me">粗框 = 你的位置</span>
      </div>

      <?php if (is_admin()): ?>
        <form method="post" class="ship-cond-form">
          <div>
            <label>今日海域</label>
            <select name="duty_zone">
              <option value="">— 未設定 —</option>
              <?php foreach (['港口','近海','外海'] as $z): ?>
                <option value="<?= h($z) ?>" <?= $today_zone===$z?'selected':'' ?>><?= h($z) ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <div>
            <label>今日海象</label>
            <select name="sea_state">
              <option value="">— 未設定 —</option>
              <?php foreach (['平靜','輕浪','中浪','大浪'] as $s): ?>
                <option value="<?= h($s) ?>" <?= $today_sea===$s?'selected':'' ?>><?= h($s) ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <button class="btn small primary" type="submit" name="act" value="set_cond"><?= icon_svg('check') ?>套用今日</button>
          <span class="cond-hint">套用後會更新今日所有值勤紀錄之海域/海象欄位。</span>
        </form>
      <?php endif; ?>
    </div>

    <?php if(is_admin()): ?>
      <div class="muted" style="margin-top:18px;font-size:13px;">
        管理者可至 <a class="inline" href="admin_status.php">勤務總覽</a> 查看與修正全員值勤。
      </div>
    <?php endif; ?>
  </div>
  <?php page_footer(); ?>
</body>
</html>
