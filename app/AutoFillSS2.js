javascript:(function() {
    // Function to fill the second form (searchForm)
    function fillSearchForm() {
        document.getElementById('firstname').value = 'Randy';
        document.getElementById('surname').value = 'Schmidt';
        document.getElementById('dob').value = '1990-12-21';
        document.getElementById('iata_o').value = 'CDG';
        document.getElementById('iata_d').value = 'AMS';
        document.getElementById('city_name').value = 'Paris';
        document.getElementById('address').value = '6969 Sanders Lights Apartment. 534 No 10;New Sharonfurt, SC 36788';
        document.getElementById('sex').value = 'M';
        document.getElementById('nationality').value = 'IDN';
        document.getElementById('nameThreshold').value = '90';
        document.getElementById('ageThreshold').value = '80';
        document.getElementById('locationThreshold').value = '90';
    }

    // Call these functions as needed
    fillSearchForm();
})();
