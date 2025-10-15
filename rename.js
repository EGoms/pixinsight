// This runs per filter and exposure (within tolerance)
// Extract the specific filter being integrated and how many active frames
// Persist that information for renaming after autocrop
if (env.name == "Integration" && env.event == "done") {
	console.noteln("[RENAME] Integration complete --- Recording number of active frames");
	if (env.group) {
		let filterMatch = String(env.group).match(/filter\s*=\s*(\w+)/);
		let frameMatch = String(env.group).match(/\((\d+)\s*active\)/);
		if (frameMatch && filterMatch) {
			let activeFrames = parseInt(frameMatch[1], 10);
			let filter = filterMatch[1];
			let filePath = engine.outputDirectory + "/custom/" + filter + ".txt";
			
			let file = new File();
			file.createForWriting(filePath);
			file.outText(activeFrames.toString());
			file.close();
		}
	}
}

// This step renames all integrated (and cropped) files to add -STACKED_<number of frames> to filename
// Opens the custom/<filter>.txt file generated during Integration to retrieve the number of frames
// Moves the files to the new names
if (env.name == "Autocrop" && env.event == "done") {
	console.noteln("[RENAME] Autocropping done. Renaming files...");
	let filterRegex = /FILTER-([A-Za-z]+)/;
	let L = new FileList(engine.outputDirectory + "/master", ["masterLight*.xisf"], false /*verbose*/ );
	L.files.forEach(filePath => {
		let filterMatch = filePath.match(filterRegex);
		if (filterMatch) {
			let extractedFilter = filterMatch[1];
			let stackedFramesFile = engine.outputDirectory + "/custom/" + extractedFilter + ".txt";
			
			let file = new File();
			file.openForReading(stackedFramesFile);
			let stacked = file.read(15, file.size);
			file.close();
						
			if (stacked > 0) {				
				let filterIndex = filePath.indexOf("_FILTER-");
				let beforeFilter = filePath.substring(0, filterIndex);
				let afterFilter = filePath.substring(filterIndex);
				let newPath = beforeFilter + "_STACKED-" + stacked + afterFilter;
				
				if (File.exists(filePath)) {
					File.move(filePath, newPath);
				} else {
					console.writeln("[RENAME] file not found");
				}
			} else {
				console.noteln("[RENAME] Could not read stacked frames for: " + filePath);
			}
		}
	})
	console.noteln("[RENAME] Renaming complete.")
}