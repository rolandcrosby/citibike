from bs4 import BeautifulSoup
import requests
import csv
import json
from pprint import pprint
from datetime import datetime

with open("config.json") as f:
    config = json.load(f)

feeds = requests.get("https://gbfs.citibikenyc.com/gbfs/gbfs.json").json()
feed = [f['url']
        for f in feeds['data']['en']['feeds']
        if f['name'] == 'station_information'
        ][0]
resp = requests.get(feed).json()
stations = resp['data']['stations']
station_map = {}
for station in stations:
    station_map[station["name"]] = (station["lat"], station["lon"])


def ins(value, arr):
    return [value] + [f for f in arr if f != value]


def write_stations(filename="stations.csv"):
    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, ins('station_id', ins('name', ins('lat', ins('lon', stations[0].keys())))))
        writer.writeheader()
        writer.writerows(stations)


s = requests.Session()

api_base = "https://webservicespublic.nyc.8d.com/bike/v1"
web_base = "https://member.citibikenyc.com"

auth = {"_username": config["citibike_username"], "_password": config["citibike_password"]}
loginpage = BeautifulSoup(s.get(web_base + "/profile/login").content, "lxml")
auth["_login_csrf_security_token"] = loginpage.find("input", attrs={"name": "_login_csrf_security_token"})["value"]
profilepage = BeautifulSoup(s.post(web_base + "/profile/login_check", auth).content, "lxml")
trips_url = [a["href"]
             for a in profilepage.find_all("a")
             if a["href"].startswith("/profile/trips/")][0]
member_id = trips_url.split("/")[3]
print(member_id)


def rentals(api_key, authorization):
    headers = {
        'api-key': api_key,
        'Authorization': authorization
    }
    response = requests.get(api_base + "/rental/closed", headers=headers)
    return response.json()["rentals"]


class Rental:
    def __init__(self, params={}):
        self.start_name = params["ss"]
        self.start_loc = station_map[self.start_name]
        self.end_name = params["es"]
        self.end_loc = station_map[self.end_name]
        self.start_time = datetime.fromtimestamp(params["sd"] / 1000.0, None)
        self.end_time = datetime.fromtimestamp(params["ed"] / 1000.0, None)
        self.duration = self.end_time - self.start_time
        self.distance = params["dm"]

    def __repr__(self):
        return "<Rental " + repr(self.__dict__) + ">"


rental_response = rentals(config["citibike_api_key"], config["citibike_authorization"])
my_rentals = [Rental(r) for r in rental_response[member_id]]
pprint(my_rentals)


def ll(tup):
    return ",".join(str(x) for x in tup)


def route(rental):
    url = "https://maps.googleapis.com/maps/api/directions/json?origin={}&destination={}&mode=bicycling&key={}"
    return requests.get(url.format(ll(rental.start_loc), ll(rental.end_loc), config["gmaps_api_key"])).json()

pprint(route(my_rentals[0]))