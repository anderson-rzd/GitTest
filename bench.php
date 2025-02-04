<?php
function benchEN($iterations) {
    $a = null;
    $start1 = microtime(true);
    for ($i = 0; $i < $iterations; $i++) {
        if ($a === null) {
            // Faz nada
        }
    }
    $end1 = microtime(true);
    $time1 = $end1 - $start1;
    echo "Tempo para \$a === null: {$time1} segundos\n";
}

function benchIN($iterations) {
    $a = null;

    $start1 = microtime(true);
    for ($i = 0; $i < $iterations; $i++) {
        if (is_null($a)) {
            // Faz nada
        }
    }
    $end1 = microtime(true);
    $time1 = $end1 - $start1;

    echo "Tempo para is_null(\$a): {$time1} segundos\n";
}

// Executar benchmark com 100.000.000 iterações
$iterations = 1000000000;
switch($argv[1]) {
    case 1:
        benchIN($iterations);
    break;
    case 2:
        benchEN($iterations);
    break;
    default:
    benchIN($iterations);
    benchEN($iterations);
}

?>

