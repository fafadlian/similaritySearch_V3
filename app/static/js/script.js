// Refactored JavaScript for Improved Cleanliness and Modularity

const App = (() => {
    // Constants and Configurations
    const API_ROUTES = {
        DELETE_TASK: '/delete_task',
        SIMILARITY_SEARCH: '/perform_similarity_search',
        GET_RESULT: '/result',
        FLIGHT_IDS: '/flight_ids',
    };

    const SELECTORS = {
        PARAM_FORM: '#paramForm',
        SEARCH_FORM: '#searchForm',
        DOWNLOAD_JSON: '#downloadJson',
        DELETE_TASK: '#deleteTask',
        LOADING_INDICATOR: '#loadingIndicator',
        SEARCH_RESULTS: '#searchResults',
        UNIQUE_FLIGHT_IDS: '#uniqueFlightIds',
        NATIONALITY: '#nationality',
        IATA_ORIGIN: '#iata_o',
        IATA_DESTINATION: '#iata_d',
    };

    let globalResponseData = []; // Initialize as an empty array
    const hoverColumns = ['FNSimilarity','SNSimilarity','AgeSimilarity', 'DOBSimilarity', 'strAddressSimilarity', 'natMatch', 'sexMatch', 'originSimilarity', 'destinationSimilarity']; // Columns to display on hover
    const displayedColumns = ['Confidence Level', 'Compound Similarity Score', 'Name', 'DOB', 'Sex', 'Nationality','Travel Doc Number', 'BookingID']; // Directly displayed columns



    // Utility Functions
    const sendRequest = (url, data = {}, method = 'POST') => {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open(method, url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
    
            xhr.onload = () => {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (xhr.status === 200) {
                        resolve(response);
                    } else {
                        reject({ status: xhr.status, message: response.message || xhr.responseText });
                    }
                } catch (error) {
                    reject({ status: xhr.status, message: "Invalid JSON response" });
                }
            };
    
            xhr.onerror = () => reject({ status: 'error', message: 'Network error' });
    
            if (method === 'GET') {
                xhr.send(); // No body for GET requests
            } else {
                xhr.send(JSON.stringify(data));
            }
        });
    };
    

    const showLoadingIndicator = () => {
        document.querySelector(SELECTORS.LOADING_INDICATOR).style.display = 'flex';
    };

    const hideLoadingIndicator = () => {
        document.querySelector(SELECTORS.LOADING_INDICATOR).style.display = 'none';
    };

    const showNotification = (message, type = 'danger') => {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.textContent = message;
        document.body.prepend(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    };

    // Handle Cleanup on Page Unload
    window.addEventListener('beforeunload', () => {
        const taskId = localStorage.getItem('task_id');
        if (taskId) {
            const data = JSON.stringify({ task_id: taskId });
            const url = API_ROUTES.DELETE_TASK;

            if (navigator.sendBeacon) {
                navigator.sendBeacon(url, data);
            } else {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', url, false); // false makes it synchronous
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(data);
            }
            localStorage.removeItem('task_id');
        }
    });

    // Dropdown Population
    const populateDropdown = (selector, csvPath, mapData) => {
        const selectElement = document.querySelector(selector);
        Papa.parse(csvPath, {
            download: true,
            header: true,
            complete: (results) => {
                const data = results.data;
                data.forEach((item) => {
                    const option = document.createElement('option');
                    const { value, label } = mapData(item);
                    option.value = value;
                    option.textContent = label;
                    selectElement.appendChild(option);
                });

                $(selectElement).select2({
                    placeholder: "Select an option",
                    allowClear: true,
                    width: '100%',
                    dropdownAutoWidth: true,
                });
            },
        });
    };

    const populateNationalityDropdown = () => {
        populateDropdown(SELECTORS.NATIONALITY, '/static/data/geoCrosswalk/GeoCrossWalkMed.csv', (item) => {
            return { value: item.HH_ISO.trim(), label: item.countryName.trim() };
        });
    };

    const populateAirportDropdowns = () => {
        populateDropdown(SELECTORS.IATA_ORIGIN, '/static/data/geoCrosswalk/GeoCrossWalkMed.csv', (item) => {
            return { value: item.IATA.trim(), label: `${item.IATA.trim()} - ${item.airportName.trim()}` };
        });
        populateDropdown(SELECTORS.IATA_DESTINATION, '/static/data/geoCrosswalk/GeoCrossWalkMed.csv', (item) => {
            return { value: item.IATA.trim(), label: `${item.IATA.trim()} - ${item.airportName.trim()}` };
        });
    };

    // Form Handlers
    const handleParamFormSubmit = (event) => {
        event.preventDefault();
        showLoadingIndicator(); // Show loading indicator
    
        const data = {
            arrival_date_from: document.querySelector('#arrivalDateFrom').value,
            arrival_date_to: document.querySelector('#arrivalDateTo').value,
            flight_nbr: document.querySelector('#flightNbr').value,
        };
    
        const previousTaskId = localStorage.getItem('task_id');
        const deleteTaskPromise = previousTaskId
            ? sendRequest(API_ROUTES.DELETE_TASK, { task_id: previousTaskId })
            : Promise.resolve();
    
        deleteTaskPromise
            .catch(() => console.log('No previous task to delete'))
            .finally(() => {
                sendRequest('/submit_param', data)
                    .then((response) => {
                        if (response.task_id) {
                            localStorage.setItem('task_id', response.task_id);
                            checkTaskStatusSSE(response.task_id); // Use SSE for real-time updates
                            showNotification('Task created successfully.', 'success');
                        } else {
                            showNotification('Task creation failed: No task ID returned.', 'danger');
                            hideLoadingIndicator();
                        }
                    })
                    .catch((err) => {
                        console.error('Error creating new task:', err);
                        showNotification('Failed to create a new task.', 'danger');
                        hideLoadingIndicator();
                    });
            });
    };
    
    
    
    

    const handleSearchFormSubmit = (event) => {
        event.preventDefault();
        showLoadingIndicator(); // Show loading indicator

        const task_id = localStorage.getItem('task_id');
        if (!task_id) {
            showNotification('Task ID not found. Please start a task first.', 'warning');
            hideLoadingIndicator();
            return;
        }
    
        const data = {
            task_id: task_id,
            firstname: document.querySelector('#firstname').value || '',
            surname: document.querySelector('#surname').value || '',
            dob: document.querySelector('#dob').value || '',
            iata_o: document.querySelector('#iata_o').value || '',
            iata_d: document.querySelector('#iata_d').value || '',
            city_name: document.querySelector('#city_name').value || '',
            address: document.querySelector('#address').value || '',
            sex: document.querySelector('#sex').value || 'None',
            nationality: document.querySelector('#nationality').value || 'None',
            nameThreshold: parseFloat(document.querySelector('#nameThreshold').value),
            ageThreshold: parseFloat(document.querySelector('#ageThreshold').value),
            locationThreshold: parseFloat(document.querySelector('#locationThreshold').value),
        };
    
        // Validate threshold values
        if (
            isNaN(data.nameThreshold) || data.nameThreshold < 0 || data.nameThreshold > 100 ||
            isNaN(data.ageThreshold) || data.ageThreshold < 0 || data.ageThreshold > 100 ||
            isNaN(data.locationThreshold) || data.locationThreshold < 0 || data.locationThreshold > 100
        ) {
            showNotification('Thresholds must be numbers between 0 and 100.', 'warning');
            hideLoadingIndicator();
            return;
        }

        console.log('Payload being sent:', data);

    
        sendRequest(API_ROUTES.SIMILARITY_SEARCH, data)
            .then((response) => {
                if (response && response.data) {
                    displayResults(response);
                } else {
                    showNotification('No similar passengers found.', 'info');
                }
            })
            .catch((err) => {
                console.error('Error during similarity search:', err);
                showNotification('Similarity search failed.', 'danger');
            })
            .finally(hideLoadingIndicator);
    };
    

    const checkTaskStatusSSE = (taskId) => {
        const eventSource = new EventSource(`/sse/${taskId}`);
    
        eventSource.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);
                console.log('Task Status:', response.status);
                console.log('Task Message:', response.message);
    
                if (response.status === 'completed') {
                    console.log('Task completed successfully.');
                    displayFlightIds(taskId); // Display the results
                    hideLoadingIndicator(); // Hide the loading indicator
                    eventSource.close(); // Close the SSE connection
                } else if (response.status === 'failed') {
                    console.error('Task failed.');
                    showNotification('Task processing failed.', 'danger');
                    hideLoadingIndicator(); // Hide the loading indicator
                    eventSource.close(); // Close the SSE connection
                } else {
                    console.log('Task is still in progress.');
                }
            } catch (err) {
                console.error('Error processing SSE message:', err);
                showNotification('Error processing SSE message.', 'danger');
            }
        };
    
        eventSource.onerror = (err) => {
            console.error('SSE connection error:', err);
            showNotification('Error checking task status via SSE.', 'danger');
            hideLoadingIndicator(); // Hide the loading indicator
            eventSource.close(); // Close the SSE connection on error
        };
    };    
    

    // Display Flight IDs
    const displayFlightIds = (taskId) => {
        sendRequest(`/flight_ids/${taskId}`, {}, 'GET')
            .then((response) => {
                const flightIds = response.flight_ids;
                const count = response.unique_flight_id_count;
                const task_id = response.task_id;
                const displayDiv = document.querySelector('#uniqueFlightIds');
                displayDiv.innerHTML = `Unique Flight IDs: ${count}<br>`;
                console.log('task_id:', task_id);   
            })
            .catch((err) => {
                console.error('Error fetching flight IDs:', err);
                showNotification('Failed to fetch flight IDs.', 'danger');
            });
    };

    const displayResults = (response) => {
        console.log("Response data:", response.data);
        globalResponseData = response.data; // Assign response data to global variable
        const resultsDiv = document.getElementById('searchResults');
        resultsDiv.innerHTML = ''; // Clear previous results
    
        if (response.data && response.data.length > 0) {
            const table = document.createElement('table');
            table.className = 'table table-striped';
    
            // Header for displayed columns
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            displayedColumns.forEach((columnName) => {
                const th = document.createElement('th');
                th.textContent = columnName;
                headerRow.appendChild(th);
            });
    
            // Header cell for "Actions"
            const actionTh = document.createElement('th');
            actionTh.textContent = "Actions";
            headerRow.appendChild(actionTh);
            thead.appendChild(headerRow);
            table.appendChild(thead);
    
            // Body with clickable details
            const tbody = document.createElement('tbody');
            response.data.forEach((item, index) => {
                const row = document.createElement('tr');
                displayedColumns.forEach((columnName) => {
                    const td = document.createElement('td');
                    td.textContent = item[columnName];
                    row.appendChild(td);
                });
    
                // Cell with a "View More" button to toggle additional details
                const toggleDetailsTd = document.createElement('td');
                const toggleDetailsBtn = document.createElement('button');
                toggleDetailsBtn.textContent = "View More";
                toggleDetailsBtn.className = 'btn btn-info btn-sm';
                toggleDetailsBtn.onclick = () => {
                    const detailsRow = document.getElementById(`details-${index}`);
                    detailsRow.style.display = detailsRow.style.display === 'none' ? '' : 'none';
                };
                toggleDetailsTd.appendChild(toggleDetailsBtn);
                row.appendChild(toggleDetailsTd);
    
                tbody.appendChild(row);
    
                // Create a hidden row for additional details
                const detailsRow = document.createElement('tr');
                detailsRow.style.display = 'none'; // Initially hidden
                detailsRow.id = `details-${index}`;
    
                const detailsCell = document.createElement('td');
                detailsCell.colSpan = displayedColumns.length + 1;
    
                const miniTable = document.createElement('table');
                miniTable.className = 'table table-hover'; // Bootstrap styles
    
                const miniThead = document.createElement('thead');
                const miniHeaderRow = document.createElement('tr');
                hoverColumns.forEach((columnName) => {
                    const miniTh = document.createElement('th');
                    miniTh.textContent = columnName;
                    miniHeaderRow.appendChild(miniTh);
                });
                miniThead.appendChild(miniHeaderRow);
                miniTable.appendChild(miniThead);
    
                const miniTbody = document.createElement('tbody');
                const miniBodyRow = document.createElement('tr');
                hoverColumns.forEach((columnName) => {
                    const miniTd = document.createElement('td');
                    miniTd.textContent = item[columnName] || '-'; // Use '-' if data is missing
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
    
        // Hide the loading indicator if applicable
        hideLoadingIndicator(); 
    };
    


    

    const handleDeleteTask = () => {
        const taskId = localStorage.getItem('task_id');
        if (taskId) {
            sendRequest(API_ROUTES.DELETE_TASK, { task_id: taskId })
                .then(() => {
                    localStorage.removeItem('task_id');
                    showNotification('Task deleted successfully.', 'success');
                })
                .catch((err) => showNotification(`Failed to delete task: ${err.message}`, 'danger'));
        } else {
            showNotification('No task found to delete.', 'warning');
        }
    };

    const handleDownloadJson = () => {
        const taskId = localStorage.getItem('task_id');
        if (!taskId) {
            showNotification('No task found. Perform a search first.', 'warning');
            return;
        }
    
        // Assuming `globalResponseData` contains the data to download
        if (!globalResponseData || globalResponseData.length === 0) {
            showNotification('No data available to download.', 'warning');
            return;
        }
    
        const jsonData = {
            task_id: taskId,
            data: globalResponseData,
        };
    
        const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `similarity_search_${taskId}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification('JSON file downloaded successfully.', 'success');
    };
    
    // Event Listeners Initialization
    const initEventListeners = () => {
        document.querySelector(SELECTORS.PARAM_FORM).addEventListener('submit', handleParamFormSubmit);
        document.querySelector(SELECTORS.SEARCH_FORM).addEventListener('submit', handleSearchFormSubmit);
        document.querySelector(SELECTORS.DELETE_TASK).addEventListener('click', handleDeleteTask);
        document.querySelector(SELECTORS.DOWNLOAD_JSON)?.addEventListener('click', handleDownloadJson);
        populateNationalityDropdown();
        populateAirportDropdowns();
    };

    // Public API
    return {
        init: () => {
            console.log('App initialized');
            initEventListeners();
        },
    };
})();

// Initialize the App
window.addEventListener('DOMContentLoaded', App.init);
