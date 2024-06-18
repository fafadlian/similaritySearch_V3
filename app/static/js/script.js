// Add this at the top or where other event listeners are added
window.addEventListener('beforeunload', function (e) {
    var task_id = localStorage.getItem('task_id');
    if (task_id) {
        var data = JSON.stringify({ task_id: task_id });
        var url = '/delete_task';
        
        // Use sendBeacon to ensure the request completes even if the page is being unloaded
        if (navigator.sendBeacon) {
            navigator.sendBeacon(url, data);
        } else {
            // Fallback to synchronous request if sendBeacon is not available
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url, false);  // false makes it synchronous
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(data);
        }
        
        // Remove the task_id from localStorage
        localStorage.removeItem('task_id');
    }
});


document.addEventListener('DOMContentLoaded', function () {

    //Navigation
    setupNavigation();

    //Populating dropdowns
    populateNationalityDropdown();
    populateAirportDropdowns();

    const displayedColumns = ['Confidence Level', 'Compound Similarity Score', 'Name', 'DOB', 'Sex', 'Nationality','Travel Doc Number', 'BookingID']; // Directly displayed columns
    const hoverColumns = ['FNSimilarity','SNSimilarity','AgeSimilarity', 'DOBSimilarity', 'strAddressSimilarity', 'natMatch', 'sexMatch', 'originSimilarity', 'destinationSimilarity']; // Columns to display on hover
    var globalResponseData = [];  // Global variable to store the response data


    //Highlighting Section
     // Identify the current section here. This is a placeholder example.
     var currentSection = "similaritySearchSection"; // Change this based on actual logic or URL

     // Remove 'active' class from all nav links first
     document.querySelectorAll('.nav-link').forEach(function(link) {
         link.classList.remove('active');
     });
 
     // Add 'active' class to the current section's nav link
     if (currentSection === "similaritySearchSection") {
         document.querySelector('a[href="#similaritySearchSection"]').classList.add('active');
     } else if (currentSection === "anomalyDetectionSection") {
         document.querySelector('a[href="#anomalyDetectionSection"]').classList.add('active');
     }
     // Extend with more else-if blocks for additional sections as needed

    var lastParam = {};

    // Handle Date Range Form Submission
        // Handle Date Range Form Submission
        document.getElementById('paramForm').addEventListener('submit', function (event) {
            event.preventDefault();
            showLoadingIndicator();
        
            var task_id = localStorage.getItem('task_id');
            if (task_id) {
                sendRequest('/delete_task', { task_id: task_id }, function(response) {
                    if (response.status === "success" || (response.status === "error" && response.message === "Task not found")) {
                        console.log("Previous task deleted successfully or not found.");
                        localStorage.removeItem('task_id');
                        initiateNewSearch();
                    } else {
                        console.error("Error deleting previous task:", response.message);
                        initiateNewSearch();
                    }
                });
            } else {
                initiateNewSearch();
            }
        });

    var lastSearchQuery = {};

    // Handle Similarity Search Form Submission
    document.getElementById('searchForm').addEventListener('submit', function(e) {
        e.preventDefault();
        showLoadingIndicator();  // Show loading indicator
    
        var firstname = document.getElementById('firstname').value || '';
        var surname = document.getElementById('surname').value || '';
        var dob = document.getElementById('dob').value || '';
        var iata_o = document.getElementById('iata_o').value || '';
        var iata_d = document.getElementById('iata_d').value || '';
        var city_name = document.getElementById('city_name').value || '';
        var address = document.getElementById('address').value || '';
        var sex = document.getElementById('sex').value || 'None';
        var nationality = document.getElementById('nationality').value || 'None';
        var nameThreshold = parseFloat(document.getElementById('nameThreshold').value);
        var ageThreshold = parseFloat(document.getElementById('ageThreshold').value);
        var locationThreshold = parseFloat(document.getElementById('locationThreshold').value);
    
        // Validate threshold values
        if (isNaN(nameThreshold) || nameThreshold < 0 || nameThreshold > 100) {
            alert('Name Threshold must be a number between 0 and 100.');
            hideLoadingIndicator();
            return;
        }
        if (isNaN(ageThreshold) || ageThreshold < 0 || ageThreshold > 100) {
            alert('Age Threshold must be a number between 0 and 100.');
            hideLoadingIndicator();
            return;
        }
        if (isNaN(locationThreshold) || locationThreshold < 0 || locationThreshold > 100) {
            alert('Location Threshold must be a number between 0 and 100.');
            hideLoadingIndicator();
            return;
        }
    
        var task_id = localStorage.getItem('task_id');  // Retrieve task_id from local storage
        var requestData = {
            task_id: task_id,
            firstname: firstname,
            surname: surname,
            dob: dob,
            iata_o: iata_o,
            iata_d: iata_d,
            city_name: city_name,
            address: address,
            sex: sex,
            nationality: nationality,
            nameThreshold: nameThreshold,
            ageThreshold: ageThreshold,
            locationThreshold: locationThreshold
        };
    
        lastSearchQuery = requestData;
    
        sendRequest('/perform_similarity_search', requestData, function(response) {
            document.getElementById('loadingIndicator').style.display = 'none'; // Hide loading indicator
            if (response && response.data) {
                console.log("Search successful:", response.message);
                displayResults(response);
            } else {
                console.error('Error in search:', response ? response.message : "No response from server");
                alert('An error occurred during search: ' + (response ? response.message : "No response from server"));
            }
        });
    });

    
    
    var downloadJsonButton = document.getElementById('downloadJson');
    if (downloadJsonButton) {
        downloadJsonButton.addEventListener('click', function() {
            console.log("Download JSON button clicked");
            var dateTimeString = new Date().toISOString().replace(/[^0-9]/g, '');
            var searchQuery = lastSearchQuery;
            var data = globalResponseData;
            console.log("Print globalResponseData", globalResponseData);
            console.log("Print data", data);
            var jsonData = {
                "PNR_Timeframe": {
                    "arrivalDateFrom": searchQuery.arrivalDateFrom,
                    "arrivalDateTo": searchQuery.arrivalDateTo,
                },
                "searchedIndividual": {
                    "FirstName": searchQuery.firstname,
                    "Surname": searchQuery.surname,
                    "DOB": searchQuery.dob,
                    "originIATA": searchQuery.iata_o,
                    "destinationIATA": searchQuery.iata_d,
                    "cityAddress": searchQuery.city_name,
                    "Address": searchQuery.address,
                    "Nationality": searchQuery.nationality,
                    "Sex": searchQuery.sex
                },
                "thresholds": {
                    "nameSimilarityThreshold": searchQuery.nameThreshold,
                    "ageSimilarityThreshold": searchQuery.ageThreshold,
                    "locationSimilarityThreshold": searchQuery.locationThreshold,
                },
                "results": data
            };
    
            var jsonString = JSON.stringify(jsonData, null, 2);
            var fileName = `similar_passengers_${dateTimeString}.json`;
            var blob = new Blob([jsonString], { type: "application/json" });
            var url = URL.createObjectURL(blob);
            var link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", fileName);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
        console.log("Download JSON button event listener attached");
    } else {
        console.log("Download JSON button not found");
    }

    document.getElementById('deleteTask').addEventListener('click', function() {
        var task_id = localStorage.getItem('task_id');
        if (task_id) {
            if (confirm("Are you sure you want to delete this task?")) {
                sendRequest('/delete_task', { task_id: task_id }, function(response) {
                    if (response.status === "success") {
                        alert("Task deleted successfully.");
                        localStorage.removeItem('task_id');
                        // Optionally, refresh the UI or redirect the user
                    } else if (response.status === "error" && response.message === "Task not found") {
                        alert("Task not found or already deleted.");
                        localStorage.removeItem('task_id');
                        // Optionally, refresh the UI or redirect the user
                    } else {
                        alert("Error deleting task: " + response.message);
                    }
                });
            }
        } else {
            alert("No task ID found in local storage.");
        }
    });
    
    
    
    

    // Function to send AJAX request to the server

    function sendRequest(url, data, callback, method = 'POST') {
        var xhr = new XMLHttpRequest();
        xhr.open(method, url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');

        xhr.onload = function () {
            console.log("XHR Load Event Triggered");
            console.log("XHR onload triggered", xhr.status);
            console.log("Raw response text:", xhr.responseText);
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                callback(response);
            } else {
                console.error("Request failed with status:", xhr.status);
                callback({ status: "error", message: xhr.responseText });
                alert("An error occurred. Please check the console for details then refresh the page.");
            }
        };

        xhr.onerror = function () {
            console.error("Request failed due to a network error");
            callback({ status: "error", message: "Network error" });
            hideLoadingIndicator(); // Ensure the loading indicator is hidden on error
        };

        if (method === 'GET') {
            xhr.send();
        } else {
            xhr.send(JSON.stringify(data));
        }
    }
    



    
    
    
    // Function to handle displaying the count
    function checkTaskStatus(taskId) {
        var intervalId = setInterval(function() {
            sendRequest(`/result/${taskId}`, {}, function(response) {
                console.log("Task Status:", response.status || response.message);
                if (response.status === 'completed' || response.message === 'Processing completed') {
                    clearInterval(intervalId);
                    // Handle the completed task here
                    console.log("Task completed with folder:", response.folder);
                    displayFlightIds(taskId);
                    document.getElementById('loadingIndicator').style.display = 'none'; // Hide loading indicator
                }
                else if (response.status === 'failed' || response.message === 'Processing failed') {
                    clearInterval(intervalId);
                    console.log("Task failed with error:", response.error);
                    console.error("Task failed with error:", response.error);
                    document.getElementById('loadingIndicator').style.display = 'none'; // Hide loading indicator
                }
            }, 'GET');
        }, 1000);  // Check every second
    }

    function displayFlightIds(taskId) {
        sendRequest(`/flight_ids/${taskId}`, {}, function(response) {
            var flightIds = response.flight_ids;
            var count = response.unique_flight_id_count;
            var displayDiv = document.getElementById('uniqueFlightIds');
            displayDiv.innerHTML = `Unique Flight IDs: ${count}<br>` ;
        }, 'GET');
    }

    function displayResults(response) {
        console.log("Response data:", response.data);
        globalResponseData = response.data;
        var resultsDiv = document.getElementById('searchResults');
        resultsDiv.innerHTML = ''; // Clear previous results
    
        if (response.data && response.data.length > 0) {
            var table = document.createElement('table');
            table.className = 'table table-striped';
    
            // Header for displayed columns
            var thead = document.createElement('thead');
            var headerRow = document.createElement('tr');
            displayedColumns.forEach(columnName => {
                var th = document.createElement('th');
                th.textContent = columnName;
                headerRow.appendChild(th);
            });
    
            // Header cell for "Actions"
            var actionTh = document.createElement('th');
            actionTh.textContent = "Actions";
            headerRow.appendChild(actionTh);
            thead.appendChild(headerRow);
            table.appendChild(thead);
    
            // Body with clickable details
            var tbody = document.createElement('tbody');
            response.data.forEach((item, index) => {
                var row = document.createElement('tr');
                displayedColumns.forEach(columnName => {
                    var td = document.createElement('td');
                    td.textContent = item[columnName];
                    row.appendChild(td);
                });
    
                // Cell with a "View More" button to toggle additional details
                var toggleDetailsTd = document.createElement('td');
                var toggleDetailsBtn = document.createElement('button');
                toggleDetailsBtn.textContent = "View More";
                toggleDetailsBtn.className = 'btn btn-info btn-sm';
                toggleDetailsBtn.onclick = function() {
                    var detailsRow = document.getElementById(`details-${index}`);
                    detailsRow.style.display = detailsRow.style.display === 'none' ? '' : 'none';
                };
                toggleDetailsTd.appendChild(toggleDetailsBtn);
                row.appendChild(toggleDetailsTd);
    
                tbody.appendChild(row);
    
                // Create a hidden row for additional details
                var detailsRow = document.createElement('tr');
                detailsRow.style.display = 'none'; // Initially hidden
                detailsRow.id = `details-${index}`;
    
                var detailsCell = document.createElement('td');
                detailsCell.colSpan = displayedColumns.length + 1;
    
                var miniTable = document.createElement('table');
                miniTable.className = 'table table-hover'; // Bootstrap styles
    
                var miniThead = document.createElement('thead');
                var miniHeaderRow = document.createElement('tr');
                hoverColumns.forEach(columnName => {
                    var miniTh = document.createElement('th');
                    miniTh.textContent = columnName;
                    miniHeaderRow.appendChild(miniTh);
                });
                miniThead.appendChild(miniHeaderRow);
                miniTable.appendChild(miniThead);
    
                var miniTbody = document.createElement('tbody');
                var miniBodyRow = document.createElement('tr');
                hoverColumns.forEach(columnName => {
                    var miniTd = document.createElement('td');
                    miniTd.textContent = item[columnName];
                    miniBodyRow.appendChild(miniTd);
                });
                miniTbody.appendChild(miniBodyRow);
                miniTable.appendChild(miniTbody);
    
                detailsCell.appendChild(miniTable);
                detailsRow.appendChild(detailsCell);
    
                tbody.appendChild(detailsRow); // Append the details row right after the main row
            });
            table.appendChild(tbody);
            resultsDiv.appendChild(table);
        } else {
            resultsDiv.textContent = 'No similar passengers found.';
        }
    
        // Function to hide the loading indicator (if applicable)
        hideLoadingIndicator(); // Ensure this function is defined elsewhere or remove this line if not needed
    }
    
    
    
    

    function safeJSONParse(text) {
        return JSON.parse(text, (key, value) => {
            if (typeof value === 'string' && value === 'NaN') return NaN;
            return value;
        });
    }

    function preprocessAndParseJSON(responseText) {
        // Replace occurrences of NaN with null in the response text
        // Ensure the replacement is safe and won't affect actual string values that might coincidentally contain "NaN"
        const safeResponseText = responseText.replace(/:\s*NaN\b/g, ": null");
        
        // Now parse the modified response text as JSON
        return JSON.parse(safeResponseText);
    }


    function setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link-container .nav-link');
        navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent the default anchor behavior
            
            // Remove 'active' class from all nav links
            navLinks.forEach(link => {
                link.classList.remove('active');
            });
            
            // Add 'active' class to the clicked link
            this.classList.add('active');
            
            // Hide all sections initially
            const sections = document.querySelectorAll('main > section');
            sections.forEach(section => {
                section.style.display = 'none'; // Hide all sections
            });
            
            // Extract the target section ID from the href and show the targeted section only
            const targetSectionId = this.getAttribute('href').substring(1); // Remove the '#' from the href value
            const targetSection = document.getElementById(targetSectionId);
            if (targetSection) {
                targetSection.style.display = 'block'; // Make the target section visible
            }
        });
    });
    }

    function populateNationalityDropdown() {
        const nationalitySelect = document.getElementById('nationality');
        const csvPath = '/static/data/geoCrosswalk/GeoCrossWalkMed.csv'; // Adjust based on your setup
    
        Papa.parse(csvPath, {
            download: true,
            header: true,
            complete: function(results) {
                let nationalities = results.data;
                
                // Sort nationalities by countryName alphabetically
                nationalities = nationalities.sort((a, b) => a.countryName.localeCompare(b.countryName));
    
                const addedNationalities = new Set(); // To track already added nationalities
    
                // Add "Unknown" option
                const unknownOption = document.createElement('option');
                unknownOption.value = '';
                unknownOption.textContent = 'Unknown';
                nationalitySelect.appendChild(unknownOption);
    
                nationalities.forEach(nationality => {
                    const countryName = nationality.countryName.trim();
                    const hhIso = nationality.HH_ISO.trim();
    
                    if (countryName && hhIso && !addedNationalities.has(hhIso)) {
                        const option = document.createElement('option');
                        option.value = hhIso;
                        option.textContent = countryName;
                        nationalitySelect.appendChild(option);
    
                        addedNationalities.add(hhIso);
                    }
                });
    
                // Initialize Select2 with search and limited scroll
                $(nationalitySelect).select2({
                    placeholder: "Select Nationality",
                    allowClear: true,
                    width: '100%', // Adjust width to fit your layout
                    dropdownAutoWidth: true
                });
            }
        });
    }
    
    function populateAirportDropdowns() {
        const originSelect = document.getElementById('iata_o');
        const destinationSelect = document.getElementById('iata_d');
        const csvPath = '/static/data/geoCrosswalk/GeoCrossWalkMed.csv'; // Adjust based on your setup
    
        Papa.parse(csvPath, {
            download: true,
            header: true,
            complete: function(results) {
                let airports = results.data;
                
                // Sort airports by IATA code alphabetically
                airports = airports.sort((a, b) => a['IATA'].localeCompare(b['IATA']));
    
                const addedAirports = new Set(); // To track already added IATA codes
    
                // Add "Unknown" option
                const unknownOption = document.createElement('option');
                unknownOption.value = '';
                unknownOption.textContent = 'Unknown';
                originSelect.appendChild(unknownOption);
                destinationSelect.appendChild(unknownOption.cloneNode(true));
    
                airports.forEach(airport => {
                    const iataCode = airport['IATA'].trim();
                    const airportName = airport['airportName'].trim();
                    const city = airport['City'].trim();
                    const country = airport['countryName'].trim();
    
                    if (iataCode && airportName && !addedAirports.has(iataCode)) {
                        const option = document.createElement('option');
                        option.value = iataCode;
                        option.innerHTML = `${iataCode} - ${airportName}, ${city}, ${country}`;
                        originSelect.appendChild(option);
                        destinationSelect.appendChild(option.cloneNode(true));
    
                        addedAirports.add(iataCode);
                    }
                });
    
                // Initialize Select2 with search and limited scroll
                $(originSelect).select2({
                    placeholder: "Origin Airport (IATA)",
                    allowClear: true,
                    width: '100%', // Adjust width to fit your layout
                    dropdownAutoWidth: true
                });
    
                $(destinationSelect).select2({
                    placeholder: "Destination Airport (IATA)",
                    allowClear: true,
                    width: '100%', // Adjust width to fit your layout
                    dropdownAutoWidth: true
                });
            }
        });
    }
    function showLoadingIndicator() {
        document.getElementById('loadingIndicator').style.display = 'flex';
    }

    function hideLoadingIndicator() {
        document.getElementById('loadingIndicator').style.display = 'none';
    }

    function initiateNewSearch() {
        var arrivalDateFrom = document.getElementById('arrivalDateFrom').value;
        var arrivalDateTo = document.getElementById('arrivalDateTo').value;
        var flightNbr = document.getElementById('flightNbr').value;
    
        var dateFrom = new Date(arrivalDateFrom);
        var dateTo = new Date(arrivalDateTo);
        var minDate = new Date('2019-01-01');
        var maxDate = new Date('2019-12-31');
        var errorMessages = document.getElementById('errorMessages');
        errorMessages.textContent = '';

        document.getElementById('loadingIndicator').style.display = 'none';

        if (dateFrom > dateTo) {
            errorMessages.textContent = 'Arrival Date From must be before Arrival Date To.';
            return;
        }

    
        if (dateFrom < minDate || dateFrom > maxDate || dateTo < minDate || dateTo > maxDate) {
            errorMessages.textContent = 'Dates must be within the year 2019.';
            return;
        }
    
        // Check if the range is within 2 weeks
        var twoWeeks = 14 * 24 * 60 * 60 * 1000; // 14 days in milliseconds
        if ((dateTo - dateFrom) > twoWeeks) {
            errorMessages.textContent = 'The date range must be within 2 weeks.';
            return;
        }
    
        var data = {
            arrival_date_from: arrivalDateFrom,
            arrival_date_to: arrivalDateTo,
            flight_nbr: flightNbr
        };
    
        document.getElementById('loadingIndicator').style.display = 'block';
    
        sendRequest('/submit_param', data, function(response) {
            console.log(response.message);
            if (response.task_id) {
                localStorage.setItem('task_id', response.task_id);
                checkTaskStatus(response.task_id);
            } else {
                console.error('Error:', response.message || 'No task ID returned');
                document.getElementById('loadingIndicator').style.display = 'none';
            }
        });
    
        lastParam = data;
    }

});
