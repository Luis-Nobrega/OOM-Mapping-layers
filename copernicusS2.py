############################################### 
# Get dependencies
###############################################

import subprocess
import sys

############################################### 
# Check for necessary package installation
############################################### 

packages = ["matplotlib", "pandas", "getpass", "sentinelhub"]

def check_and_install_package():
    try:
        # Check if pip is installed
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'])
    except subprocess.CalledProcessError:
        print("pip is not installed. Please install pip and try again.")
        sys.exit(1)
    for package in packages:
        try:
            # Check if the package is installed
            __import__(package)
        except ImportError:
            print(f"{package} is not installed. Installing...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        else:
            print(f"{package} is already installed.")

#check_and_install_package()

############################################### 
# Package installation
############################################### 

import matplotlib.pyplot as plt
import pandas as pd
import getpass

from sentinelhub import (
    SHConfig,
    DataCollection,
    SentinelHubCatalog,
    SentinelHubRequest,
    SentinelHubStatistical,
    BBox,
    bbox_to_dimensions,
    CRS,
    MimeType,
    Geometry,
)

# from utils import plot_image
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from datetime import date
from PIL import Image
import numpy as np
import datetime
from datetime import timedelta, datetime

############################################### 
# Sentinel Hub login 
############################################### 


client_id = "your_client_id_from_copernicus.eu" # both expire at 01 January 2026, 23:59 (UTC) 
client_secret = "your_secret_id_from_copernicus.eu" # enter account and make a new request

##### IF used for first time, uncomment this part #####

#config = SHConfig()
#config.sh_client_id = client_id
#config.sh_client_secret = client_secret
#config.sh_base_url = 'https://sh.dataspace.copernicus.eu'
#config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
#config.save("cdse")

config = SHConfig("cdse") # Use sentinel hub after the first configuration

# Create a session
client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)

# Get token for the session
token = oauth.fetch_token(token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
                          client_secret=client_secret, include_client_id=True)

# All requests using this session will have an access token automatically added
resp = oauth.get("https://sh.dataspace.copernicus.eu/configuration/v1/wms/instances")
print(resp.content)

# requests-oauthlib doesn't check for status before checking if the response is ok. This gives the correct error if it occurs
def sentinelhub_compliance_hook(response):
    response.raise_for_status()
    return response

oauth.register_compliance_hook("access_token_response", sentinelhub_compliance_hook)

############################################### 
# Data retrieval area
############################################### 

aoi_coords_wgs84 = [-17.567139,32.296420,-16.040039,33.312168] # set coords for interest area

resolution = 60 # resoltution (don't change this, it's already the maximum)
aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)
aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)

print(f"Image shape at {resolution} m resolution: {aoi_size} pixels")

################# Sentinel Hub Catalog API (or shortly “Catalog”)

catalog = SentinelHubCatalog(config=config) 

aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)

############################################### 
# JSON for internal image instructions 
############################################### 

evalscript_true_color = """
    //VERSION=3

    function setup() {
        return {
            input: [{
                bands: ["B02", "B03", "B04"]
            }],
            output: {
                bands: 3
            }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
"""

evalscript_SWIR = """
//VERSION=3
let minVal = 0.0;
let maxVal = 0.4;

let viz = new HighlightCompressVisualizer(minVal, maxVal);

function setup() {
  return {
    input: ["B12", "B8A", "B04","dataMask"],
    output: { bands: 4 }
  };
}

function evaluatePixel(samples) {
    let val = [samples.B12, samples.B8A, samples.B04,samples.dataMask];
    return viz.processList(val);
}
"""

evalscript_NDWI = """
//VERSION=3
//ndwi
const colorRamp1 = [
  	[0, 0xFFFFFF],
  	[1, 0x008000]
  ];
const colorRamp2 = [
  	[0, 0xFFFFFF],
  	[1, 0x0000CC]
  ];

let viz1 = new ColorRampVisualizer(colorRamp1);
let viz2 = new ColorRampVisualizer(colorRamp2);

function setup() {
  return {
    input: ["B03", "B08", "SCL","dataMask"],
    output: [
		{ id:"default", bands: 4 },
        { id: "index", bands: 1, sampleType: "FLOAT32" },
        { id: "eobrowserStats", bands: 2, sampleType: 'FLOAT32' },
        { id: "dataMask", bands: 1 }
	]
  };
}

function evaluatePixel(samples) {
  let val = index(samples.B03, samples.B08);
  let imgVals = null;
  // The library for tiffs works well only if there is only one channel returned.
  // So we encode the "no data" as NaN here and ignore NaNs on frontend.
  const indexVal = samples.dataMask === 1 ? val : NaN;
  
  if (val < -0) {
    imgVals = [...viz1.process(-val), samples.dataMask];
  } else {
    imgVals = [...viz2.process(Math.sqrt(Math.sqrt(val))), samples.dataMask];
  }
  return {
    default: imgVals,
    index: [indexVal],
    eobrowserStats:[val,isCloud(samples.SCL)?1:0],
    dataMask: [samples.dataMask]
  };
}

function isCloud(scl) {
  if (scl == 3) {
    // SC_CLOUD_SHADOW
    return false;
  } else if (scl == 9) {
    // SC_CLOUD_HIGH_PROBA
    return true;
  } else if (scl == 8) {
    // SC_CLOUD_MEDIUM_PROBA
    return true;
  } else if (scl == 7) {
    // SC_CLOUD_LOW_PROBA
    return false;
  } else if (scl == 10) {
    // SC_THIN_CIRRUS
    return true;
  } else if (scl == 11) {
    // SC_SNOW_ICE
    return false;
  } else if (scl == 1) {
    // SC_SATURATED_DEFECTIVE
    return false;
  } else if (scl == 2) {
    // SC_DARK_FEATURE_SHADOW
    return false;
  }
  return false;
}
"""

############################################### 
# Retireve dates, and jpeg format
############################################### 

current_date = (f"{date.today().year}-{date.today().month}-{int(date.today().day) - 5}",f"{date.today().year}-{date.today().month}-{int(date.today().day)}")
mode = "mostRecent" # can be "mostRecent" or "leastCC"

def date_chooser():
    time_interval = date.today() - timedelta(days = 10), date.today()
    search_iterator = catalog.search(
        DataCollection.SENTINEL2_L2A, # DataCollection.SENTINEL3_OLCI, use this for other data 
        bbox=aoi_bbox,
        time=time_interval,
        fields={"include": ["id", "properties.datetime"], "exclude": []},
    )

    results = list(search_iterator)
    tile_to_find = "_R023_"
    desired_date = None

    for result in results:
        if tile_to_find in result['id']:
            desired_date = result['properties']['datetime'][:10]  # Extract the date part in format YYYY-MM-DD
            break  # Stop once we find the date

    # Step 2: Filter results to include only the images from the desired date
    if desired_date:
        previous_date = datetime.strptime(desired_date, "%Y-%m-%d") - timedelta(days=1)
        formatted_date = previous_date.strftime('%Y-%m-%d')
    
        return (formatted_date, desired_date)
    else:
        raise ValueError("No adequate data found in chosen period")


def save_image_as_jpeg(image_array, filename):
    # Convert the numpy array to a PIL image
    image = Image.fromarray(np.uint8(image_array))
    
    # Check if the image has an alpha channel and convert it to RGB if necessary
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    # Save the image as JPEG
    image.save(filename, "JPEG")
    print(f"Image saved as {filename}")

############################################### 
# Sentinel data request and setup area
############################################### 

def request_sentinel(data, image_name, change_date=1, start_date="2022-05-01", end_date="2022-05-20"):
    # Determine the time interval based on change_date
    time_interval = (start_date, end_date) if change_date == 0 else current_date

    # Create the SentinelHubRequest
    treated_data = SentinelHubRequest(
        evalscript=data,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    name="s3olci", service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=time_interval,
                other_args={"dataFilter": {"mosaickingOrder": mode}},
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],  # TIFF is often better for scientific data
        bbox=aoi_bbox,  
        size=aoi_size,  
        config=config,  
    )

    final_data = treated_data.get_data()
    save_image_as_jpeg(final_data[0], image_name)

# To see what satellite passages are available 

def available_data():
  time_interval = date.today() - timedelta(days = 6), date.today()
  search_iterator = catalog.search(
      DataCollection.SENTINEL2_L2A, # DataCollection.SENTINEL3_OLCI, use this for other data 
      bbox=aoi_bbox,
      time=time_interval,
      fields={"include": ["id", "properties.datetime"], "exclude": []},
  )

  results = list(search_iterator)
  for element in results:
      print(element)

############################################### 
# Setup and testing area
############################################### 

vals = [evalscript_true_color, evalscript_SWIR, evalscript_NDWI]
image_names = ["TRUE_COL2.jpeg", "SWIR2.jpeg", "NDWI2.jpeg"]

cnt = 0
for element in vals:
    request_sentinel(element, image_names[cnt],0, date_chooser()[0], date_chooser()[1]) # automatically choose date (can lead to cut image)!!!
    #request_sentinel(element, image_names[cnt],0,  start_date="2024-08-28", end_date="2024-08-30") # manually choose date 
    cnt+=1

available_data() # to search available slots for debugging 
print(f"Used date: {date_chooser()[1]}")
