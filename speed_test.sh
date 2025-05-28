#!/bin/bash

URL="http://127.0.0.1:443/combined_operation"

ranges=(
    "1_day 2019-02-01 2019-02-02"
    "1_week 2019-02-01 2019-02-08"
    "10_days 2019-02-01 2019-02-11"
    "2_weeks 2019-02-01 2019-02-15"
    "1_month 2019-02-01 2019-03-01"
)

echo "Measuring response times for different date ranges..."

for range in "${ranges[@]}"; do
    # Split the range into key, start_date, and end_date
    IFS=' ' read -r key start_date end_date <<< "$range"

    echo -e "\n🔹 **Testing range: $key ($start_date to $end_date)**"

    # Create a temporary JSON file
    temp_json=$(mktemp)
    cat > "$temp_json" <<EOF
{
    "arrival_date_from": "$start_date",
    "arrival_date_to": "$end_date",
    "flight_nbr": "",
    "firstname": "collin",
    "surname": "brown",
    "dob": "1968-10-15",
    "iata_o": "DXB",
    "iata_d": "BUD",
    "city_name": "",
    "address": "",
    "sex": "M",
    "nationality": "INA",
    "nameThreshold": 80,
    "ageThreshold": 80,
    "locationThreshold": 80
}
EOF

    # Send the request using the temporary JSON file
    time curl -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d @"$temp_json" \
    -w "\nTime Total: %{time_total}s\nTime Namelookup: %{time_namelookup}s\nTime Connect: %{time_connect}s\nTime StartTransfer: %{time_starttransfer}s\n" \
    -o /dev/null -s

    # Remove temporary JSON file
    rm -f "$temp_json"
done
