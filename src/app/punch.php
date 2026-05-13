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
    $stmt = $pdo->prepare("SELECT * FROM attendance WHERE user_id=? AND work_date=? FOR UPDATE");
    $stmt->execute([$uid, $d]);
    $row = $stmt->fetch();

    if ($act === 'in') {
      if (!$row) {
        $ins = $pdo->prepare("INSERT INTO attendance(user_id, work_date, check_in, status) VALUES(?,?,?,'open')");
        $ins->execute([$uid, $d, $now]);
        $msg = "值勤開始：{$now}";
      } else if (empty($row['check_in'])) {
        $upd = $pdo->prepare("UPDATE attendance SET check_in=?, status='open' WHERE att_id=?");
        $upd->execute([$now, (int)$row['att_id']]);
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

    // SVG coordinate map: cx/cy = dot centre, lx/ly = label anchor, ta = text-anchor
    $pos_coords = [
      '艦橋'   => ['cx'=>338, 'cy'=>68,  'lx'=>338, 'ly'=>42,  'ta'=>'middle'],
      '瞭望台' => ['cx'=>338, 'cy'=>28,  'lx'=>374, 'ly'=>28,  'ta'=>'start' ],
      '前甲板' => ['cx'=>128, 'cy'=>140, 'lx'=>128, 'ly'=>157, 'ta'=>'middle'],
      '後甲板' => ['cx'=>538, 'cy'=>140, 'lx'=>538, 'ly'=>157, 'ta'=>'middle'],
      '通訊室' => ['cx'=>248, 'cy'=>108, 'lx'=>248, 'ly'=>95,  'ta'=>'middle'],
      '機艙'   => ['cx'=>488, 'cy'=>170, 'lx'=>520, 'ly'=>170, 'ta'=>'start' ],
    ];
    $st_zh_map = ['on'=>'值勤中','done'=>'已結束','leave'=>'請假','off'=>'未值勤'];
    ?>

    <div class="card ship-card">
      <div class="card-head">
        <h2>今日艦上人員配置</h2>
        <span class="muted" style="font-size:13px;"><?= h($d) ?> · 星期<?= h($wd) ?></span>
      </div>
      <svg class="ship-svg" viewBox="0 0 680 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="艦上人員配置示意圖">
        <!-- Hull -->
        <path class="sh-hull" d="M28,175 L70,128 L618,128 L644,152 L644,188 L28,188 Z"/>
        <!-- Deck railing (dashed lines fore/aft of superstructure) -->
        <line class="sh-railing" x1="72"  y1="128" x2="210" y2="128"/>
        <line class="sh-railing" x1="468" y1="128" x2="617" y2="128"/>
        <!-- Superstructure block -->
        <rect class="sh-struct" x="210" y="85" width="258" height="43" rx="2"/>
        <!-- Bridge on top -->
        <rect class="sh-struct" x="235" y="52" width="208" height="35" rx="3"/>
        <!-- Mast & antenna crosspiece -->
        <line class="sh-mast" x1="338" y1="52" x2="338" y2="12"/>
        <line class="sh-mast" x1="308" y1="24" x2="368" y2="24"/>
        <circle cx="338" cy="12" r="3" fill="var(--muted)" opacity=".35"/>
        <!-- Funnel -->
        <rect class="sh-funnel" x="385" y="64" width="24" height="24" rx="2"/>
        <!-- Bridge windows -->
        <rect class="sh-window" x="252" y="61" width="14" height="9" rx="1"/>
        <rect class="sh-window" x="274" y="61" width="14" height="9" rx="1"/>
        <rect class="sh-window" x="296" y="61" width="14" height="9" rx="1"/>
        <rect class="sh-window" x="370" y="61" width="14" height="9" rx="1"/>
        <rect class="sh-window" x="392" y="61" width="14" height="9" rx="1"/>
        <rect class="sh-window" x="414" y="61" width="14" height="9" rx="1"/>
        <!-- Superstructure portholes -->
        <circle class="sh-porthole" cx="228" cy="107" r="5"/>
        <circle class="sh-porthole" cx="254" cy="107" r="5"/>
        <circle class="sh-porthole" cx="434" cy="107" r="5"/>
        <circle class="sh-porthole" cx="460" cy="107" r="5"/>
        <!-- Hull portholes -->
        <circle class="sh-porthole" cx="100" cy="158" r="4"/>
        <circle class="sh-porthole" cx="126" cy="158" r="4"/>
        <circle class="sh-porthole" cx="152" cy="158" r="4"/>
        <circle class="sh-porthole" cx="508" cy="158" r="4"/>
        <circle class="sh-porthole" cx="536" cy="158" r="4"/>
        <circle class="sh-porthole" cx="564" cy="158" r="4"/>
        <!-- Bow anchor detail -->
        <path class="sh-detail" d="M70,175 L50,168 L44,158"/>
        <!-- Waterline -->
        <line class="sh-water" x1="24" y1="178" x2="648" y2="178"/>

        <?php foreach ($pos_coords as $pos_name => $c):
          $people = $pos_groups[$pos_name] ?? [];
          $n = count($people);
        ?>
          <text class="sh-pos-lbl" x="<?= $c['lx'] ?>" y="<?= $c['ly'] ?>" text-anchor="<?= $c['ta'] ?>"><?= h($pos_name) ?></text>
          <?php if ($n === 0): ?>
            <circle class="sh-dot off" cx="<?= $c['cx'] ?>" cy="<?= $c['cy'] ?>" r="11"/>
          <?php else: ?>
            <?php foreach ($people as $i => $person):
              $offset = (int)round(($i - ($n - 1) / 2.0) * 28);
              $cx    = $c['cx'] + $offset;
              $cy    = $c['cy'];
              $st    = $person['status'];
              $me    = $person['is_me'] ? ' me' : '';
              $init  = mb_substr($person['name'], 0, 1);
              $tfill = ($st === 'on' || $st === 'done') ? '#fff' : 'var(--muted)';
              $st_zh = $st_zh_map[$st];
            ?>
              <g class="sh-crew-marker">
                <title><?= h($person['name']) ?> · <?= $st_zh ?></title>
                <circle class="sh-dot <?= h($st.$me) ?>" cx="<?= $cx ?>" cy="<?= $cy ?>" r="12"/>
                <text class="sh-init" x="<?= $cx ?>" y="<?= ($cy + 4) ?>" text-anchor="middle" fill="<?= $tfill ?>"><?= h($init) ?></text>
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
