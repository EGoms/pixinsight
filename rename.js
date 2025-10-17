// Astrometric solutioning is the last step in the stacking pipeline. After thats is complete files will be renamed with additional info
// Use the groups information to extract the active frames per Filter as well as the total exposure time
// Add these to the generated file name
if (env.name === "Astrometric solution" && env.event === "done") {
	console.noteln("[RENAME] Solving done. Renaming files...");

	//Filter -> [frames, total exposure]
	let data = {
		L: [0, 0],
		R: [0, 0],
		G: [0, 0],
		B: [0, 0],
		S: [0, 0],
		H: [0, 0],
		O: [0, 0]
	}

    let postGroups = engine.groupsManager.groupsForMode(WBPPGroupingMode.POST);
    for ( let i = 0; i < postGroups.length; ++i ) {
		let filter = postGroups[i].filter
		let frameMatch = String(postGroups[i]).match(/\((\d+)\s*active\)/);
		if (frameMatch && filter) {
			data[filter][0] = parseInt(frameMatch[1], 10);
		}
		data[filter][1] = postGroups[i].totalExposureTime();
    }

	let filterRegex = /FILTER-([A-Za-z]+)/;
	let L = new FileList(engine.outputDirectory + "/master", ["masterLight*.xisf"], false /*verbose*/);
	L.files.forEach(filePath => {
		let filterMatch = filePath.match(filterRegex);
		if (filterMatch) {
			let extractedFilter = filterMatch[1];
			if (extractedFilter === env.group.filter) {
				let stacked = data[extractedFilter][0];
				let expTime = data[extractedFilter][1];
				if (stacked > 0 && expTime > 0) {
					let filterIndex = filePath.indexOf("_mono_");
					let newPath = filePath.substring(0, filterIndex) + "_FRAMES-" + stacked + "_TOTAL-" + expTime + filePath.substring(filterIndex);
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