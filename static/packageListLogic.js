// When a modal's submit button is clicked, we need some way of getting the package ID that
// the modal is for. This function is called just before the modal is opened. It will put the
// package ID into a hidden input on the modal so it can be retrieved later.
function assignPackageIDToModal(packageID, modalName) {
	$("#" + modalName + "-packageIDHolder").val(parseInt(packageID));
}

// Called when the user clicks the dialog button to rename or delete their package.
// modalName should be the css ID of the modal that called this function.
// Since the modal HTML elements have ids that are prefixed by the modal name, we just put
// the modal name in front of an id to get the element of the active modal
function handleModalSubmit(modalName) {
	// Disable the 3 buttons
	$("#" + modalName + "-xButton").prop("disabled", true);
	$("#" + modalName + "-cancelButton").prop("disabled", true);
	$("#" + modalName + "-updateButton").prop("disabled", true);

	// Add HTML - this is a little bootstrap spinner loading thing
	$("#" + modalName + "-modal-footer").append('<div class="spinner-border text-primary" id="' + modalName + '-loadingSpinner" role="status"><span class="visually-hidden">Loading...</span></div>');
	// Make the error message hidden - new request, no error
	$("#" + modalName + "-modalErrorMessage").removeClass("d-inline");
	$("#" + modalName + "-modalErrorMessage").addClass("d-none");

	var packageID = $("#" + modalName + "-packageIDHolder").val();

	// This request will send the request to the flask endpoint
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = () => {
		// State = 4 means request has completed
		if (xhttp.readyState == 4) {
			// Remove loading indicator and re-enable all of the buttons
			$("#" + modalName + "-loadingSpinner").remove();
			$("#" + modalName + "-xButton").prop("disabled", false);
			$("#" + modalName + "-cancelButton").prop("disabled", false);
			$("#" + modalName + "-updateButton").prop("disabled", false);

			// If the request was a success then we can hide the modal
			if(xhttp.status == 200 && xhttp.responseText != "0") {
				// Update the package label with the new title
				if(modalName == "titleInputModal")
					$("#packageLabel-" + packageID).text(xhttp.responseText);
				else if(modalName == "deleteModal")
					removePackageFromList(packageID);
					
				// Hide modal and reset text input field
				bootstrap.Modal.getInstance(document.getElementById(modalName)).hide();
				$("#new-title-input").val("");
			}
			// If it failed then we show the error messge
			else {
				$("#" + modalName + "-modalErrorMessage").removeClass("d-none");
				$("#" + modalName + "-modalErrorMessage").addClass("d-inline");
			}
		}
	};

	// Send the request to flask - contains new title and package ID,
	// or just the package ID if we are deleting.
	// Encode the paramters to stay safe :-) !!!
	if(modalName == "titleInputModal"){
		xhttp.open("POST", "updatePackageTitle", true);
		xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
		xhttp.send("newTitle=" + encodeURIComponent($("#new-title-input").val()) + "&packageID=" + encodeURIComponent(packageID));
	}
	else if(modalName == "deleteModal") {
		xhttp.open("POST", "deletePackage", true);
		xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
		xhttp.send("packageID=" + encodeURIComponent(packageID));
	}
}

function removePackageFromList(id) {
	// First, remove it from the list
	$("#packageListAccordionItem-" + id).remove();
	// If there are no more packages, then we need to add the default prompt
	if($("#packageListAccordion").children().length == 0)
		$("#main-container").append("<h6>You are not tracking any packages. Add one!</h6>");
}

// This function is the logic for the accordion. It is called when the accordion expands.
// It does the UI stuff and loads the package data from the backend.
function accordionExpanding(packageID) {
	// Show a loading icon
	$("#accordion-body-" + packageID).append('<div class="spinner-border text-primary" id="' + packageID + '-loadingSpinner" role="status"><span class="visually-hidden">Loading...</span></div>');
	
	// This will send the request to the flask endpoint
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = () => {
		// State = 4 means request has completed
		if (xhttp.readyState == 4) {
			// Hide spinner
			$("#accordion-body-" + packageID).find("#" + packageID + "-loadingSpinner").remove();

			let packageData = undefined;
			if(xhttp.status == 200)
				packageData = JSON.parse(xhttp.responseText);

			// Only accept if there was both a succesfull response (200) and the backend didnt give us an error
			if(packageData && packageData["success"] == true) {
				$("#accordion-body-" + packageID).append("<ul class='list-group'></ul>");
			
				if(packageData["data"].length < 2) {
					$("#accordion-body-" + packageID + " > ul").append("<li class='list-group-item' style='border: 1px solid black; margin-bottom: 5px;'>There is no tracking data for this package yet. Please try again in a few minutes.</li>");
				}
				// If there is tracking data, then we add it to the <ul>
				// Slice at 1 to remove my metadata that I added to my SQL query
				else {
					packageData["data"].slice(1).forEach(data => {
						// Had to move this here from the jinja template to make it doable
						$("#accordion-body-" + packageID + " > ul").append(`
						<li class="list-group-item" style="border: 1px solid black; margin-bottom: 5px;">
							<p class="fst-italic" style="margin-bottom: 5px;">${data["date"]}</p>
							<span class="badge rounded-pill bg-primary">${data["time"]}</span>
							<p style="margin-top: 5px;">${data["data"]}</p>
						</li>
						`);
					});
				}
			}
			// If it failed then we show a neat little information thing that will be hidden when the accordion collapses
			else {
				$("#accordion-body-" + packageID).append("<p class='text-danger'>Something went wrong. Please try again.</p>");
			}
		}
	}

	//Yeet
	xhttp.open("POST", "packageData", true);
	xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	xhttp.send("packageID=" + encodeURIComponent(packageID));
}

// Need to register events for accordion expansion and collapse
$(document).ready(() => {
	// Accordion is collapsing - remove all data and error labels
	$(".accordion-item").on("hidden.bs.collapse", e => {
		let packageID = e.currentTarget.id.split("-")[1];
		$("#accordion-body-" + packageID).children().remove("*");
	});

	$(".accordion-item").on("shown.bs.collapse", e => {
		let packageID = e.currentTarget.id.split("-")[1];
		accordionExpanding(packageID);
	});
});