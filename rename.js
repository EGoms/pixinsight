secondsToHms = function (d) {
    d = Number(d);
    var h = Math.floor(d / 3600);
    var m = Math.floor(d % 3600 / 60);
    var s = Math.floor(d % 3600 % 60);

	var hDisplay = h > 0 ? h + "h" : "";
    var mDisplay = m > 0 ? m + "m" : "";
    var sDisplay = s > 0 ? s + "s" : "";
    return hDisplay + mDisplay + sDisplay;
}

generateExpStr = function (g) {
	let frameMatch = String(g).match(/\((\d+)\s*active\)/);
	let timeStr = secondsToHms(g.totalExposureTime());
	if (frameMatch && timeStr !== "") {
		timeStr += "(" + parseInt(frameMatch[1], 10) + ")";
	}
	return timeStr;
}

// Astrometric solutioning is the last step in the stacking pipeline. After thats is complete files will be renamed with additional info
// Use the groups information to extract the active frames per Filter as well as the total exposure time
// Add these to the generated file name
if (env.name === "Astrometric solution" && env.event === "done") {
	console.noteln("[RENAME] Solving done. Renaming files...");

	//Filter -> [frames, total exposure]
	let times = {
		L: "",
		R: "",
		G: "",
		B: "",
		S: "",
		H: "",
		O: ""
	}

    let postGroups = engine.groupsManager.groupsForMode(WBPPGroupingMode.POST);
    for ( let i = 0; i < postGroups.length; ++i ) {
		let filter = postGroups[i].filter
		times[filter] = generateExpStr(postGroups[i]);
    }

	let filterRegex = /FILTER-([A-Za-z]+)/;
	let L = new FileList(engine.outputDirectory + "/master", ["masterLight*.xisf"], false /*verbose*/);
	L.files.forEach(filePath => {
		let filterMatch = filePath.match(filterRegex);
		if (filterMatch) {
			let extractedFilter = filterMatch[1];
			if (extractedFilter === env.group.filter) {
				let expTime = times[extractedFilter];
				if (expTime !== "") {
					let filterIndex = filePath.indexOf("_mono_");
					let newPath = filePath.substring(0, filterIndex) + "_TOTAL-" + expTime + filePath.substring(filterIndex);
					if (File.exists(filePath)) {
						File.move(filePath, newPath);
					} else {
						console.noteln("[RENAME] file not found")
					}
				} else {
					console.noteln("[RENAME] Could not read stacked frames for: " + filePath);
				}
			}
		}
	})
	console.noteln("[RENAME] Renaming complete.")
}