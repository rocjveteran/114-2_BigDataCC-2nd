<?php
// index.php - entry point
session_start();

if (isset($_SESSION['user_id'])) {
  header("Location: punch.php");
  exit;
}
header("Location: login.php");
exit;
