import xml.etree.ElementTree as ET
import os
import pandas as pd
from datetime import datetime

def compute_relative_age(df):
    today = pd.Timestamp("today")
    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
    df["relative_age"] = (today - df["dob"]).dt.days / 365.25
    df["relative_age"] = df["relative_age"].fillna(df["relative_age"].mean())
    return df


def parse_dob(date_str, pivot_year=2019):
    if not date_str or len(date_str) != 7:
        return None
    try:
        dt = datetime.strptime(date_str, "%d%b%y")
        # Apply custom pivot logic
        two_digit_year = int(date_str[-2:])
        century = 2000 if two_digit_year <= (pivot_year % 100) else 1900
        return dt.replace(year=century + two_digit_year)
    except Exception:
        return None

def parse_large_pnr_xml(xml_path, last_modified=None):
    flight_id = os.path.basename(xml_path).split('.')[0]
    context = ET.iterparse(xml_path, events=("start", "end"))
    _, root = next(context)

    flight_info = {}
    for event, elem in context:
        tag = elem.tag

        if event == "end" and tag == "FlightLeg":
            flight_info = {
                "flight_id": flight_id,
                "carrier": elem.attrib.get("CarrierCode"),
                "flight_number": elem.attrib.get("FlightNumber"),
                "departure_time": elem.attrib.get("DepartureDateTime"),
                "arrival_time": elem.attrib.get("ArrivalDateTime"),
                "departure_airport": elem.find("DepartureAirport").attrib.get("LocationCode"),
                "arrival_airport": elem.find("ArrivalAirport").attrib.get("LocationCode"),
            }

        elif event == "end" and tag == "PNR":
            booking_ref = elem.find("BookingRefID").attrib.get("ID")

            contact = elem.find("ContactInfo")
            address = contact.findtext("AddressLine", "") if contact is not None else ""
            city = contact.findtext("CityName", "") if contact is not None else ""
            country = contact.findtext("CountryName", "") if contact is not None else ""
            email = contact.attrib.get("EmailAddress", "") if contact is not None else ""
            phone = contact.attrib.get("PhoneNumber", "") if contact is not None else ""

            for pax in elem.findall("Passenger"):
                docs = pax.findall("DOC_SSR")
                doc_dict = {d.attrib.get("SSR_Code"): d.find(d.attrib.get("SSR_Code")) for d in docs if d.find(d.attrib.get("SSR_Code")) is not None}

                doc_data = doc_dict.get("DOCS")
                doco_data = doc_dict.get("DOCO")
                doca_data = doc_dict.get("DOCA")

                passenger_data = {
                    "last_modified": last_modified,
                    "booking_ref": booking_ref,
                    "travel_doc": doco_data.attrib.get("TravelDocNbr") if doco_data is not None else None,
                    "firstname": pax.findtext("GivenName", ""),
                    "surname": pax.findtext("Surname", ""),
                    "dob": parse_dob(doc_data.attrib.get("DateOfBirth") if doc_data is not None else None),
                    "gender": doc_data.attrib.get("Gender") if doc_data is not None else None,
                    "nationality": doc_data.attrib.get("PaxNationality") if doc_data is not None else None,
                    "email": email,
                    "phone": phone,
                    "address": doca_data.attrib.get("Address") if doca_data is not None else address,
                    "postal_code": doca_data.attrib.get("PostalCode") if doca_data is not None else "",
                    "city": doca_data.attrib.get("CityName") if doca_data is not None else city,
                    "country": doca_data.attrib.get("Country") if doca_data is not None else country,
                    **flight_info,
                }
                yield passenger_data

            elem.clear()
    root.clear()
