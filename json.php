<?php

function kibiize($value) {

	$kunits = array(
		array("prefix" => "E", "multi" => 1152921504606846976),
		array("prefix" => "P", "multi" => 1125899906842624),
		array("prefix" => "T", "multi" => 1099511627776),
		array("prefix" => "G", "multi" => 1073741824),
		array("prefix" => "M", "multi" => 1048576),
		array("prefix" => "k", "multi" => 1024),
		array("prefix" => "", "multi" => 1),
	);

	$i = 0;

	for ($i = 0; $i < sizeof($kunits); $i++) {
		if ($value > $kunits[$i]["multi"]) {
			$value /= $kunits[$i]["multi"];
			return sprintf("%.2f&nbsp;%sB", $value, $kunits[$i]["prefix"]);
		}
	}
}

function get_extension($filename) {
	$info = pathinfo($filename);
	return $info["extension"];
}

function format_url_to_ressource($abspath) {
	$uri = "https://media.riton.fr";
	$resource = preg_replace('/^\/var\/www\/media\//', "", $abspath);
	$uri .= "$resource";
	#return $uri;
	return rawurlencode($uri);
}

function dir_to_array($path, $dir) {
	$abs_path;
	if (isset($dir)) {
		$abs_path = "$path/$dir";
	}else {
		$abs_path = $path;
	}

	$dirh = opendir($abs_path);
	if ($dirh === false) {
		exit(1);
	}

	$full_content = array();

	while (($entry = readdir($dirh)) !== false) {
		if (preg_match('/^\./', $entry) === 1) {
			continue;
		}

		$entry_t = filetype("$abs_path/$entry");
		if ($entry_t == "dir") {
			$content = dir_to_array($abs_path, $entry);
			array_push($full_content, $content);
		}
		else {
			$stats = stat("$abs_path/$entry");
			$size = $stats[7];
			array_push($full_content, array($entry, $size, format_url_to_ressource("$abs_path/$entry")));
		}
	}
	
	closedir($dirh);

	return array($dir => $full_content);
}

$dir = "/var/www/media/";

$array = dir_to_array($dir, "Incoming");
$json = json_encode($array);
echo "$json\n";

exit(0);

