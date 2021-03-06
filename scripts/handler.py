#!/usr/bin/python

from pathfinder import pathFinder

import urllib2
import json
import googlemaps
from urllib import quote
from os import environ

import cgitb, cgi
cgitb.enable()

print("Content-Type: text/html\n")

# If you're looking at this project, please don't steal/abuse this API key.
googleKey = "AIzaSyADJzDYaO0we1opZUxxUULc8yFgD1W5nKo"
azureKey = "gkYlkVyl1Z2eA0IZWe/Qr4I/JDT0RsKCHl3ggAaeRKQqQ6ehY4EXgD0yze9NYdOopXPIzKH9bB2h8e5PopOQFA=="
numWaypoints = 2

# We don't check that the fields weren't blank. That kind of data integrity
# assurance can get thrown out the window in a 24 hour hackathon.
def entryPoint():

    form = cgi.FieldStorage()

    gmaps = googlemaps.Client(googleKey)

    # This captures if the script is run from the webpage.
    # If not, we just hard code some values for testing purposes.
    if 'GATEWAY_INTERFACE' in environ:
        origin = form["origin"].value
        destination = form["destination"].value
    else:
        origin = "ANU, Canberra"
        destination = "Parliament House, Canberra"

    originCoords = getCoords(origin, gmaps)
    destinationCoords = getCoords(destination, gmaps)

    # Generate the pathing points for which we want to check the probabilities.
    testPoints = pathFinder(originCoords, destinationCoords)

    # Check the probabilities of each of these points and append to the list
    # a tuple with the point coords and its risk probability.
    probs = []
    for point in testPoints:
        res = getAzureProbability(point[0], point[1])
        probs.append((point, res))

    # Get 2 (numWayPoints) lowest waypoints.
    waypoints = sorted(probs, key=lambda x: x[1])[:numWaypoints]
    
    # Convert these waypoints to strings for compiling the http request to the
    # Google Maps embed API.
    stringWaypoints = []
    for i in waypoints:
        stringWaypoints.append(str(i[0][0]) + "," + str(i[0][1]))

    # Build the final Google Maps iframe HTML to 
    # insert into the webpage with AJAX jQuery.
    compileMapsRequest(origin, destination, stringWaypoints)


# Get the coordinates of a given address.
def getCoords(address, gmaps):
    ret = gmaps.geocode(address, {"country":"au"})
    if len(ret) == 0:
        print "Couldn't geolocate " + address
        return None
    else:
        coords = ret[0]["geometry"]["location"]
        return [coords["lat"], coords["lng"]]


# Using hardcoded HTML build up the google maps iframe to be returned.
# The quote function makes a string HTML safe. 
def compileMapsRequest(origin, destination, waypoints):
    base = """
                <div class="row">
                    <iframe
                      width="1215"
                      height="675"
                      frameborder="0" style="border:0"
                      src='
            """

    urlTarget = "https://www.google.com/maps/embed/v1/directions?key="
    key = googleKey

    end = """
                        &mode=bicycling' allowfullscreen>
                    </iframe>
                </div>
            """
            
    # Create the request as a list of components.
    requestParts = []
    # Build the base request.
    requestParts.append("&origin=")
    requestParts.append(quote(origin))
    requestParts.append("&destination=")
    requestParts.append(quote(destination))

    # If we have waypoints, add them to the request.
    if len(waypoints) > 0:
        requestParts.append("&waypoints=")
        # Add waypoints
        for wp in waypoints[:-1]:
            requestParts.append(quote(wp))
            requestParts.append("|")
        # Add last one without the pipe.
        requestParts.append(quote(waypoints[-1]))

    # Rebuild the string from the components.
    request = "".join(requestParts)

    # Compile the final request and print it (via CGI).
    finalString = base + urlTarget + key + request + end
    print finalString


"""
Create the request for Azure ML. Currently just checks the probability at midday.
For some reason Azure ML needs quite a bit of extra crap in the request, but we're
just following the (very useful) API that it generates for us.

The request comes back as json and we unpack the final proability with the quite
convoluted index dereferencing of ["Results"]["output1"]["value"]["Values"][0][-1].
There is likely a more elegant method of pulling off this task, but as it is it 
still works quite solidly. 

We return the final probability as a float.
"""
def getAzureProbability(latitude, longitude):

    baseHour = 12

    data =  {

            "Inputs": {

                    "input1":
                    {
                        "ColumnNames": ["long", "lat", "time", "event"],
                        "Values": [ [ longitude, latitude, baseHour, "0" ], [ "0", "0", "0", "0" ], ]
                    },        },
                "GlobalParameters": {
    }
        }

    body = str.encode(json.dumps(data))

    url = 'https://ussouthcentral.services.azureml.net/workspaces/0188131680ce420794e35a3a48d85416/services/bbc6c1a5e65241b397a0b6e3a52a4a91/execute?api-version=2.0&details=true'
    api_key = azureKey
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}

    req = urllib2.Request(url, body, headers) 

    try:
        response = urllib2.urlopen(req)

        # If you are using Python 3+, replace urllib2 with urllib.request in the above code:
        # req = urllib.request.Request(url, body, headers) 
        # response = urllib.request.urlopen(req)

        result = response.read()
        return float(json.loads(result)["Results"]["output1"]["value"]["Values"][0][-1])
    except urllib2.HTTPError, error:
        print("The request failed with status code: " + str(error.code))
        # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
        print(error.info())
        print(json.loads(error.read()))

        return None                 


entryPoint()

