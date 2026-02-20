import argparse
import json
import requests
from requests_oauth2client import OAuth2Client, OAuth2ClientCredentialsAuth
import traceback

from datetime import datetime, time, timedelta, timezone
from io import StringIO
from pprint import pprint

#------------------------------------------------------------------------------

api = "https://api.churchsuite.com/v2/"
api_request_count = 0

# The list of resources associated with the West Wing
westwing_resources = [
    'West Hall (Front)',
    'West Hall (Back)',
    'Multifunction Room 1 (MFR1)',
    'Multi-Function Room 2 (MFR2)',
    'Flexible Use Room (FUR)',
    'West Wing Kitchenette',
    'Music Room 1 (MR1)',
    'Music Room 2 (MR2)',
    'West Wing Meeting Room (WWMR)',
    'Playground',
    'Ball Playing Area',
    'Garden area'
    ]

# The list of resources associated with the East Wing
eastwing_resources = [
    'Main hall (Front)',
    'Main Hall (Back)',
    'Play Room',
    'TCC Main Kitchen',
    'TCC Meeting Room',
    'Mezzanine',
    'Mezz Kitchenette',
    'Recording Studio',
    'TCC Prayer Room',
    'Playground',
    'Ball Playing Area',
    'Garden area'
    ]

schedule_template_file = "ScheduleTemplate.html"
output_path = "./"

#------------------------------------------------------------------------------

# Create an OAuth2 session from client credentials
# From https://stackoverflow.com/questions/76736460/automatic-token-fetching-with-oauth2-client-credentials-flow-with-python-request
def create_oauth2_session(client_id, client_secret, base_url, scope="full_access"):
    token_url = f"{base_url}/oauth2/token"

    oauth2client = OAuth2Client( token_endpoint=token_url, client_id=client_id, client_secret=client_secret)
    auth = OAuth2ClientCredentialsAuth( oauth2client, scope=scope, resource=base_url)

    session = requests.Session()
    session.auth = auth
    return session

#------------------------------------------------------------------------------

# Collect JSON data from the specified endpoint
def get_api_data(session, endpoint, params=None):

    global api_request_count
    api_request_count = api_request_count + 1

    try:
        r = session.get(api + endpoint, params=params)
        if r.status_code == 200:
            return r.json().get('data')
        else:
            print(f"ERROR: API access to '{endpoint}' failed with {r.status_code}.")
            exit()
    except:
        print(f"ERROR: API access to '{endpoint}' failed.")
        raise

    return None

#------------------------------------------------------------------------------

# Collect all of the required data from ChurchSuite
def collect_api_data(session, starting_from, num_days):

    yesterday = datetime.combine(starting_from + timedelta(-1), time.min)
    tomorrow = yesterday + timedelta(num_days + 1)
    params = {"per_page": 250, "starts_after": f"{yesterday.strftime('%Y-%m-%d')}", "starts_before": f"{tomorrow.strftime('%Y-%m-%d')}"}

    # See https://developer.churchsuite.com/calendar#tag/events/GET/calendar/events
    events = get_api_data(session, "calendar/events", params=params)
    # pprint(events)

    # See https://developer.churchsuite.com/bookings#tag/bookings/GET/bookings/bookings
    bookings = get_api_data(session, "bookings/bookings", params=params)
    # pprint(bookings)

    # See https://developer.churchsuite.com/bookings#tag/resources/GET/bookings/resources
    resources = get_api_data(session, "bookings/resources")
    # pprint(resources)

    # See https://developer.churchsuite.com/account#tag/sites/GET/account/sites
    sites = get_api_data(session, "account/sites")
    # pprint(sites)

    # See https://developer.churchsuite.com/account#tag/brands/GET/account/brands/default
    brand = get_api_data(session, "account/brands/default")
    # pprint(brand)

    return sites, events, bookings, resources

#------------------------------------------------------------------------------

# Map the list of site_ids to site names
def get_site_names(sites, site_ids):
    site_names = [x['name'] for x in sites if x["id"] in site_ids]
    return site_names

# Map the resources_id to a single resource name
def get_resource(resources, resource_id):
    resource = [x for x in resources if x["id"] == resource_id]
    return resource[0]  # Assume there is only one

# Lookup the resources associated with a specific booking
def get_booked_resources(session, booking_id):
    # See https://developer.churchsuite.com/bookings#tag/resources/GET/bookings/booked_resources
    params = {"booking_ids[]": f"{booking_id}"}
    booked_resources = get_api_data(session, "bookings/booked_resources", params=params)
    # pprint(booked_resources)
    return booked_resources

# Lookup the event associated with a specific event id
def get_event(session, event_id):
    # See https://developer.churchsuite.com/calendar#tag/events/GET/calendar/events/{id}
    event = get_api_data(session, f"calendar/events/{event_id}")
    # pprint(event)
    return event

#------------------------------------------------------------------------------

# Show resources for each event
def show_events(session, sites, events, bookings, resources):
    # TODO: TCC doesn't seem to be using events - nothing to show
    pass

# Show resources for each booking
def show_bookings(session, sites, events, bookings, resources):

    for b in bookings:
        booking_id = b['id']            # Integer
        event_id = b['event_id']        # Integer|null
        name = b['name']                # String
        description = b['description']  # String
        starts_at = datetime.fromisoformat(b['starts_at'])  # String e.g. 2026-01-22T19:30:00Z
        ends_at = datetime.fromisoformat(b['ends_at'])      # String e.g. 2026-01-22T19:30:00Z
        site_ids = b['site_ids']        # Integer[]

        if event_id != None:
            event = get_event(session, event_id)
            event_name = event['name']                  # String
            event_description = event['description']    # String
            print(f"Event {event_id}: {event_name}, {event_description}")
        else:
            print(f"Booking {booking_id}: {name}, {description}")

        site_names = get_site_names(sites, site_ids)
        print(f"  At {site_names} from {starts_at.ctime()} to {ends_at.ctime()}")

        print("  Resources:")
        booked_resources = get_booked_resources(session, booking_id)
        for br in booked_resources:
            booked_resource_id = br['resource_id']  # Integer
            resource = get_resource(resources, booked_resource_id)
            # pprint(resource)
            name = resource['name']                 # String
            description = resource['description']   # String
            all_sites = resource['all_sites']       # Boolean
            site_ids = resource['site_ids']         # Integer[]
            print(f"    {booked_resource_id}: {name}, {description}")

#------------------------------------------------------------------------------

# Show resources for each booking
def extract_schedule(session, sites, bookings, resources):

    schedule = []

    for b in bookings:
        booking_id = b['id']            # Integer
        event_id = b['event_id']        # Integer|null
        booking_name = b['name']                # String
        booking_description = b['description']  # String
        starts_at = datetime.fromisoformat(b['starts_at'])  # String e.g. 2026-01-22T19:30:00Z
        ends_at = datetime.fromisoformat(b['ends_at'])      # String e.g. 2026-01-22T19:30:00Z
        site_ids = b['site_ids']        # Integer[]

        if event_id != None:
            event = get_event(session, event_id)
            event_name = event['name']                  # String
            event_description = event['description']    # String
        else:
            # If no event is linked then fall-back to booking name & description
            event_name = booking_name
            event_description = booking_description

        site_names = get_site_names(sites, site_ids)

        booked_resources = get_booked_resources(session, booking_id)
        for br in booked_resources:
            booked_resource_id = br['resource_id']  # Integer
            resource = get_resource(resources, booked_resource_id)
            resource_name = resource['name']                 # String

            schedule.append({'sites': site_names, 'starts': starts_at, 'ends': ends_at, 'name': event_name, 'description': event_description, 'resource': resource_name})

	# Sort by start time
    schedule = sorted(schedule, key=lambda x: x['starts'])

	# Extract events associated with rooms in the East Wing
    schedule_eastwing = [x for x in schedule if x['resource'] in eastwing_resources]
    build_schedule_page(schedule_eastwing, eastwing_resources, schedule_template_file, f"The Carraig Centre &ndash; East Wing Events Today", output_path + "EastWingSchedule.html")

	# Extract events associated with rooms in the West Wing
    schedule_westwing = [x for x in schedule if x['resource'] in westwing_resources]
    build_schedule_page(schedule_westwing, westwing_resources, schedule_template_file, f"The Carraig Centre &ndash; West Wing Events Today", output_path + "WestWingSchedule.html")

#------------------------------------------------------------------------------

# Create an HTML table representing the schedule and insert it into the specified HTML page template
def build_schedule_page(schedule, rooms, template_file, title, save_as):
    # Assumes the schedule is sorted and all events are within a single day

    time_interval = 30 * 60  # seconds

    # Calculate the number of table columns between the two datetime objects
    def column_count(earlier, later):
        return int((later - earlier).total_seconds() / time_interval)

    table_html = StringIO()

    # Determine the earliest & latest displayed events
    # With stupid mode selector
    if False and len(schedule) > 0:
        # Earliest booking to latest booking, start rounded to hour boundary
        start_time = schedule[0]['starts'].replace(minute=0, second=0, microsecond=0)
        end_time = max(schedule, key=lambda x: x['ends'])['ends']
    elif True:
        # Fixed duration from current hour boundary
        start_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours = 6)
    else:
        # Fixed time range
        start_time = datetime.combine(datetime.today(), time(hour=9, minute=0), timezone.utc)
        end_time = datetime.combine(datetime.today(), time(hour=18, minute=0), timezone.utc)
    max_cols = column_count(start_time, end_time)

    print("<table>", file=table_html)

    # Generate the header
    print("  <tr>\n    ", end="", file=table_html)
    t = start_time
    while t < end_time:
        print(f"<th>{t.strftime('%H:%M')}</th>", end="", file=table_html)
        t += timedelta(seconds=time_interval)
    print("\n  </tr>", file=table_html)

    # Generate a row for each room (resource)
    num_rows = 0
    for r in rooms:
        # Get the events for this room
        events_in_room = [x for x in schedule if x['resource'] == r]
        # Only generate rows for rooms that have bookings
        if not events_in_room:
            continue
        num_rows = num_rows + 1
        print("  <tr>", file=table_html)
        print(f"    <!-- {r} -->", file=table_html)

        num_cols = 0
        for e in events_in_room:
            start = column_count(start_time, e['starts'])
            duration = column_count(e['starts'], e['ends'])
            # Truncate any events starting before start of schedule
            if start < 0:
                duration = start + duration
                start = 0
            # Skip events beyond the current period
            if start >= max_cols:
                continue
            # Truncate any events ending after the end of schedule
            duration = min(duration, max_cols - start)
            # Skip events in the past
            if duration <= 0:
                continue
            
            # Here (0 <= start < max_cols) and (0 < duration <= max_cols-start)
            # Calculate the gap between the end of the previous event and the start of this one
            gap = start - num_cols
            if gap < 0:
                # This event overlaps with the previous event - shift start
                start = start + gap
                duration = duration + gap
                if duration <= 0:
                     continue
            elif gap > 0:
                # Create empty cells before event, if needed
                print("    " + "<td class='empty'></td>" * gap, file=table_html)
            # Create the event itself
            print(f"    <!-- {e['name']} in {r} from {e['starts'].strftime('%H:%M')} to {e['ends'].strftime('%H:%M')} -->", file=table_html)
            print(f"    <td class='room-{num_rows}' colspan='{duration:.0f}'>{e['name']}<span>{r}</span></td>", file=table_html)
            num_cols = num_cols + gap + duration

        # Create empty cells at end of day, if needed
        gap = max_cols - num_cols
        if gap > 0:
            print("    " + "<td class='empty'></td>" * gap, file=table_html)
        print("  </tr>", file=table_html)

    # Create empty rows, if needed
    gap = len(rooms) - num_rows
    for _ in range(gap):
        print("  <tr>", file=table_html)
        print("    <!-- Padding -->", file=table_html)
        print("    " + "<td class='empty'></td>" * max_cols, file=table_html)
        print("  </tr>", file=table_html)

    print("</table>", file=table_html)

    # Create the complete page
    with open(template_file) as f: 
        output = f.read()
    output = output.replace("*** Insert title here ***", title)
    output = output.replace("*** Insert today's date here ***", datetime.today().strftime("%A, %d %B %Y"))
    output = output.replace("*** Insert timestamp here ***", datetime.today().ctime())
    output = output.replace("*** Insert schedule table here ***", table_html.getvalue())
    output = output.replace("*** Insert last updated here ***", "Last updated at " + datetime.today().strftime("%H:%M on %A, %d %B %Y"))
    with open(save_as,"wt") as f: 
        f.write(output)

    print(f"Generated {save_as}.")

#------------------------------------------------------------------------------

def main():

	# Get configuration
	credentials = None
	try:
		with open('./credentials.json') as f:
			credentials = json.load(f)
			# pprint(credentials)
			f.close()
	except FileNotFoundError:
		print(f"ERROR: The {'./credentials.json'} file does not exist.")
		return

	session = create_oauth2_session(credentials['client_identifier'], credentials['client_secret'], credentials['token_resource'])

	# Collect only events occuring today
	start_of_today = datetime.combine(datetime.now(), time.min)
	num_days = 1
	sites, events, bookings, resources = collect_api_data(session, start_of_today, num_days)
	print(f"Found:")
	print(f"  {len(sites)} sites.")
	print(f"  {len(events)} events.")
	print(f"  {len(bookings)} bookings.")
	print(f"  {len(resources)} resources.")

	#show_bookings(session, sites, bookings, resources)
	#show_events(session, sites, events, bookings, resources)

	extract_schedule(session, sites, bookings, resources)

	print(f"Made {api_request_count} API requests.")

#------------------------------------------------------------------------------

if __name__ == "__main__":

	try:
		main()
	except Exception as e:
		pass
		print(traceback.format_exc())
