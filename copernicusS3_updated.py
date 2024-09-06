############################################### 
# Get dependencies
###############################################

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
from datetime import date, timedelta, datetime
from PIL import Image
import numpy as np
import numpy.ma as ma
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib import pyplot as plt
import re

############################################### 
# First time setup and sentinel request
###############################################

client_id = "sh-3b0bf63f-19dc-4f95-a542-0570e457d16f" # both expire at 01 January 2026, 23:59 (UTC) 
client_secret = "2b8dVHvsbbvXKmjh4ZHMOR39dSMrKK08" # enter account and make a new request 

# IF first time running, uncomment this part

#config = SHConfig()
#config.sh_client_id = client_id
#config.sh_client_secret = client_secret
#config.sh_base_url = 'https://sh.dataspace.copernicus.eu'
#config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
#config.save("cdse")

config = SHConfig("cdse") # Use sentinel hub after the first configuration (try not to use the other one as it may overload token requests)

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

aoi_coords_wgs84 = [-17.954016,32.018547,-15.878085,33.601334] # Aproximate area 

resolution = 80 # resoltution (don't change this, it's already the maximum for these coordinates)
aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)
aoi_size = bbox_to_dimensions(aoi_bbox, resolution=resolution)

print(f"Image shape at {resolution} m resolution: {aoi_size} pixels")

################# Sentinel Hub Catalog API (or shortly “Catalog”)

catalog = SentinelHubCatalog(config=config) 

aoi_bbox = BBox(bbox=aoi_coords_wgs84, crs=CRS.WGS84)


current_date = (f"{date.today().year}-{date.today().month}-{int(date.today().day) - 5}",f"{date.today().year}-{date.today().month}-{int(date.today().day)}")
print(f"Today is: {current_date[1]}")

############################################### 
# JSON for internal image instructions 
###############################################

# The formula was adapted from one conveived for data from MODIS satelite 
# Updated evaluation script for Sentinel-3 OLCI -> https://earth.esa.int/eogateway/documents/20142/37627/cawa-algorithm-theoretical-basis-water-vapor.pdf
evalscript_sentinel3_olci_IWV = """
//VERSION=3

let rangeMin = 0; 
let rangeMax = 70;  
let viz = ColorRampVisualizer.createOceanColor(rangeMin, rangeMax);

function setup() {
  return {
    input: [{
      bands: ["B18", "B19", "dataMask"]
    }],
    output: { bands: 4 }
  }
}

function evaluatePixel(samples) {
  if (samples.dataMask === 0) {
    return [0, 0, 0, samples.dataMask];
  }
  
  let B18 = samples.B18;
  let B19 = samples.B19;
  let C1 = 0.0746699;
  let C2 = -1.15649;
  let C3 = 19.9892;
  
  // Calculate the value based on the formula
  let value = (2 * C1 - Math.log(B19) * C2 +  Math.log(B19) * Math.log(B19) * C3 ) / 10;

  // Apply visualization to the calculated value
  let color = viz.process(value);

  return [...color, samples.dataMask];
}
"""

# 2022_Rodrigues_etal_remotesensing.pdf CHL-a in mg/m^3 http://www.jeeng.net/pdf-152428-77647?filename=The%20Interaction%20of.pdf
evalscript_sentinel3_olci_CHL = """
//VERSION=3

let rangeMin = 0; 
let rangeMax = 1;  
let viz = ColorRampVisualizer.createOceanColor(rangeMin, rangeMax);

function setup() {
  return {
    input: [{
      bands: ["B03", "B04", "B05", "B06", "dataMask"]
    }],
    output: { bands: 4 }
  }
}

function evaluatePixel(samples) {
  if (samples.dataMask === 0) {
    return [0, 0, 0, samples.dataMask];
  }
  
  let B3 = samples.B03;
  let B4 = samples.B04;
  let B5 = samples.B05;
  let B6 = samples.B06;
  let A0 = 0.450;
  let A1 = -3.259;
  let A2 = 3.522; 
  let A3 = -3.359;
  let A4 =  0.949; 
  let R = Math.log10(Math.max(B3/B6, B4/B6, B5/B6))
  
  // Calculate the Chl-a value based on the given formula
  let chlA = Math.pow(10, A0 + A1*R + A2*R*R + A3*R*R*R + A4*R*R*R*R) 

  // Apply visualization to the calculated value
  let color = viz.process(chlA);

  return [...color, samples.dataMask];
}
"""
# Total surface matter TSM=a×Rrs​(B17) + b Nechad et al. (2010). -> https://www.sciencedirect.com/science/article/pii/S0272771415000396
evalscript_sentinel3_olci_TSM = """
//VERSION=3

let rangeMin = 0;
let rangeMax = 80;  
let viz = ColorRampVisualizer.createOceanColor(rangeMin, rangeMax);

function setup() {
  return {
    input: [{
      bands: ["B08", "B06", "dataMask"] // Using B07 which corresponds to Oa07 (665 nm)
    }],
    output: { bands: 4 }
  }
}

function evaluatePixel(samples) {
  if (samples.dataMask === 0) {
    return [0, 0, 0, samples.dataMask];
  }
  
  let B6 = samples.B06;
  let B8 = samples.B08;

  // Calculate TSM using an alternative empirical relationship
  let tsm = 190.37 * Math.pow(B8/B6,2) - 138.61 * B8/B6 + 26.883

  // Apply visualization
  let color = viz.process(tsm);

  return [...color, samples.dataMask];
}
"""

# AAE=−ln(AOD(λ2​)AOD(λ1​)​)​/ln(λ1/λ2) -> Aerosol Angstrom Exponent (AAE) (more close to Aerosol optical thickness)
evalscript_sentinel3_olci_AAE = """
//VERSION=3

let rangeMin = 0.8;  
let rangeMax = 3;   
let viz = ColorRampVisualizer.createOceanColor(rangeMin, rangeMax);

function setup() {
  return {
    input: [{
      bands: ["B06", "B17", "dataMask"]
    }],
    output: { bands: 4 }
  }
}

function evaluatePixel(samples) {
  if (samples.dataMask === 0) {
    return [0, 0, 0, samples.dataMask];
  }
  
  let AOD_B01 = samples.B06;  
  let AOD_B02 = samples.B17;  

  // Calculate AAE
  let aae = -Math.log(AOD_B01 / AOD_B02) / Math.log(510 / 865);

  // Apply visualization
  let color = viz.process(aae);

  return [...color, samples.dataMask];
}
"""
# SST=c0​+c1​×T10.8​+c2​×(T10.8​−T12.0​)+c3​×(T10.8​−T12.0​)^2 -> Sea surface temperature 
evalscript_sentinel3_olci_OTCI = """
//VERSION=3 
const map = [ 
	[0.0, 0x00007d],
	[1.0, 0x004ccc],
	[1.8, 0xff3333],
	[2.5, 0xffe500],
	[4.0, 0x00cc19],
	[4.5, 0x00cc19],
	[5.0,0xffffff]
];

const visualizer = new ColorRampVisualizer(map);
function setup() {
	return {
		input: [ "B10", "B11", "B12", "dataMask" ],
        output: [
		{ id: "default", bands: 4 },
		{ id: "index", bands: 1, sampleType: "FLOAT32" },
        { id: "eobrowserStats", bands: 1 },
        { id: "dataMask", bands: 1},
    	]
	};
}
    
function evaluatePixel(samples) {
    let OTCI = (samples.B12- samples.B11)/(samples.B11- samples.B10);
    let imgVals = null;
    // The library for tiffs works well only if there is only one channel returned.
    // So we encode the "no data" as NaN here and ignore NaNs on frontend.
    // we restrict the interval to [-10, 10] as it covers most of the value range
    const indexVal = samples.dataMask === 1 && OTCI >= -10 && OTCI <= 10 ? OTCI : NaN;
    imgVals = [...visualizer.process(OTCI), samples.dataMask]
    return {
        default: imgVals,
        index: [indexVal],
        eobrowserStats:[indexVal],
        dataMask: [samples.dataMask]      
    };
 }
"""

evalscript_sentinel3_olci_RGB = """
//VERSION=3 (auto-converted from 1)
let minVal = 0.0;
let maxVal = 0.8;

let viz = new HighlightCompressVisualizer(minVal, maxVal);

function evaluatePixel(samples) {
    let val = [samples.B17, samples.B05, samples.B02, samples.dataMask];
    return viz.processList(val);
}

function setup() {
  return {
    input: [{
      bands: ["B17", "B05", "B02" , "dataMask" ]
    }],
    output: { bands: 4 }
  }
}
"""

############################################### 
# JPEG and Sentinel Hub requests 
###############################################

def save_image_as_jpeg(image_array, filename):
    # Convert the numpy array to a PIL image
    image = Image.fromarray(np.uint8(image_array))
    
    # Check if the image has an alpha channel and convert it to RGB if necessary
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    # Save the image as JPEG
    image.save(filename, "JPEG")
    print(f"Image saved as {filename}")


def request_sentinel(data, image_name, change_date=1, start_date="2022-05-01", end_date="2022-05-20", save=0):
    # Determine the time interval based on change_date
    time_interval = (start_date, end_date) if change_date == 0 else current_date

    # Create the SentinelHubRequest
    treated_data = SentinelHubRequest(
        evalscript=data,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL3_OLCI.define_from(
                    name="s3olci", service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=time_interval,
                other_args={"dataFilter": {"mosaickingOrder": "mostRecent"}},
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],  # TIFF is often better for scientific data
        bbox=aoi_bbox,  
        size=aoi_size,  
        config=config,  
    )

    final_data = treated_data.get_data()
    if save == 0:
      save_image_as_jpeg(final_data[0], image_name)
    else: 
       return final_data[0]


vals = [evalscript_sentinel3_olci_IWV, evalscript_sentinel3_olci_CHL, evalscript_sentinel3_olci_TSM, evalscript_sentinel3_olci_AAE, 
        evalscript_sentinel3_olci_OTCI, evalscript_sentinel3_olci_RGB]
image_names = ["IWV.jpeg", "CHL.jpeg", "TSM.jpeg", "AAE.jpeg", "OTCI.jpeg", "RGB.jpeg"] # all files to be created 
excluded = ["OTCI.jpeg", "RGB.jpeg"] # files not to have cloud coverage 
units = [f"kg m\u2212\u00B2", f"µg L\u207B\u00B9", f"mg L\u207B\u00B9","N/A", "N/A", "N/A"] # define units to appear in legend here 


############################################### 
# Cloud mask
###############################################

def apply_transparency(reference_image_path, original_image_path, output_image_path):
    # Load images
    reference_image = Image.open(reference_image_path)
    original_image = Image.open(original_image_path).convert("RGBA")  # Ensure original image is in RGBA format

    # Convert images to numpy arrays
    ref_array = np.array(reference_image)
    orig_array = np.array(original_image)

    # Create masks
    rgb_sum = np.sum(ref_array[:, :, :3], axis=-1)
    sum_mask = rgb_sum >= 180 # 600 for pure white
    
    # Stardard values 50 50 100 -> change for small intervals 
    specific_rgb_mask = (ref_array[:, :, 0] < 50) & (ref_array[:, :, 1] < 50) & (ref_array[:, :, 2] > 100) # adjust for sensibility but Idk why tf this is so sensible
    combined_mask = sum_mask | specific_rgb_mask

    # Set masked pixels to white [255, 255, 255, 255]
    #orig_array[combined_mask] = [255, 255, 255, 255] # for using OTCI instead of RGB
    orig_array[sum_mask] = [255, 255, 255, 255]
    # Convert back to an image
    result_image = Image.fromarray(orig_array, "RGBA")
    
    # Save the result image as PNG to preserve RGBA mode
    result_image.save(output_image_path, "PNG")
    print(f"Image with cloud masked saved as {output_image_path}")

# Apply cloud mask 
def cloud_mask():
  for name in image_names:
      if name in excluded:
          continue
      else:
          apply_transparency('RGB.jpeg', name, name )

############################################### 
# Land mask
###############################################

def land_filter(filename, units="N/A"):
  data_crs = ccrs.PlateCarree()
  coast = cfeature.GSHHSFeature(scale='full')

  # Create the figure and axis with the map projection
  fig = plt.figure(figsize=(12, 9))
  ax = fig.add_subplot(projection=data_crs)

  # Add land and coastline features
  ax.add_feature(cfeature.LAND, zorder=10)
  ax.add_feature(coast, linewidth=1.2, zorder=10)

  #aoi_coords_wgs84 = [-17.954016, 32.018547, -15.878085, 33.601334]  # [lon_min, lat_min, lon_max, lat_max]
  ax.set_extent([aoi_coords_wgs84[0], aoi_coords_wgs84[2], aoi_coords_wgs84[1], aoi_coords_wgs84[3]], crs=data_crs) 

  image_path = filename
  image = Image.open(image_path).convert("RGBA")  # Ensure image is in RGBA format

  image_extent = [aoi_coords_wgs84[0], aoi_coords_wgs84[2], aoi_coords_wgs84[1], aoi_coords_wgs84[3]]  # [lon_min, lon_max, lat_min, lat_max]

  # Display the image on the map
  ax.imshow(image, origin='upper', extent=image_extent, transform=data_crs, zorder=2)

  # Add gridlines with labels
  gl = ax.gridlines(draw_labels=True, color="None", xlocs=np.arange(-20, -14, 1), ylocs=np.arange(31, 36, 1))
  gl.top_labels = False
  gl.right_labels = False
  gl.ylabel_style = {'rotation': 90}

  # Set the title for the plot
  savename = filename.split(".")[0]
  plt.title(f"{savename} {units} @ " + str(current_date[1]))

  # Save the plot
  print(f"Image with land masked saved as {filename}")
  plt.savefig(filename, dpi=300, bbox_inches='tight', format='jpeg')

x_coords = np.linspace(aoi_coords_wgs84[0], aoi_coords_wgs84[2], aoi_size[0]) 
y_coords = np.linspace(aoi_coords_wgs84[1], aoi_coords_wgs84[3], aoi_size[1]) 
x, y = np.meshgrid(x_coords, y_coords)

def land_mask():
  cnt = 0
  for name in image_names:
      if name in excluded:
          continue
      else:
          land_filter(name, units[cnt])
      cnt += 1

############################################### 
# Add legend and colourbar
############################################### 

def create_ocean_colormap_image(rangeMin, rangeMax, width, height, output_filename, style='jet'):
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(width / 100, height / 100))  # figsize in inches

    # Generate dummy gradient data for colorbar
    gradient = np.linspace(rangeMin, rangeMax, 100).reshape(1, -1)  # Gradient with fixed width
    gradient = np.tile(gradient, (height, 1))  # Extend gradient to desired height

    # Display the dummy image
    cax = ax.imshow(gradient, aspect='auto', cmap=style, extent=[0, width, rangeMin, rangeMax])

    # Remove axis ticks and labels
    ax.axis('off')

    # Create the colorbar
    cbar = fig.colorbar(cax, orientation='horizontal', ax=ax, fraction=1.0, pad=0.0, extend='both')
    cbar.ax.tick_params(labelsize=10)  # Adjust font size of tick labels

    # Set colorbar background color to white
    #cbar.outline.set_visible(False)
    cbar.ax.set_facecolor('white')

    # Remove extra space around the figure
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)

    # Save as a JPEG image
    plt.savefig(output_filename, format='jpeg', bbox_inches='tight', dpi=300, pad_inches=0.0)
    plt.close(fig)

    print(f"Colorbar image saved as {output_filename}")

def image_merge(image_path, legend_path):

    image1 = Image.open(image_path)
    image2 = Image.open(legend_path)

    image1_size = image1.size
    image2_size = image2.size

    # Create a new image with width equal to the wider image and height equal to the sum of both images' heights
    new_width = max(image1_size[0], image2_size[0])
    new_height = image1_size[1] + image2_size[1]
    new_image = Image.new("RGB", (new_width, new_height), (250, 250, 250, 255))

    # Paste the images
    new_image.paste(image1, (0, 0))
    new_image.paste(image2, (0, image1_size[1]))

    new_image.save(image_path)

def extract_values(input_string):
    # Regular expression pattern to match minVal and maxVal
    pattern = r'let\s+rangeMin\s*=\s*(\d+\.?\d*);.*?let\s+rangeMax\s*=\s*(\d+\.?\d*);'
    
    # Search for the pattern in the input string
    match = re.search(pattern, input_string, re.DOTALL)
    
    if match:
        # Extract values from the matched groups
        min_val = float(match.group(1))
        max_val = float(match.group(2))
        return min_val, max_val
    else:
        raise ValueError("Values not found in the input string")

def legends():
   cnt = 0
   for element in image_names:
      if element in excluded:
         continue
      else:  
        min_val, max_val = extract_values(vals[cnt])
        create_ocean_colormap_image(min_val, max_val, 950, 100, 'colorbar_only.jpeg') # temporary name to be overwritten 
        image_merge(element, "colorbar_only.jpeg")
      cnt += 1
        
############################################### 
# Define appropriate running date 
###############################################

def date_chooser():
    time_interval = date.today() - timedelta(days = 3), date.today()
    search_iterator = catalog.search(
        DataCollection.SENTINEL3_OLCI, # DataCollection.SENTINEL3_OLCI, use this for other data 
        bbox=aoi_bbox,
        time=time_interval,
        fields={"include": ["id", "properties.datetime"], "exclude": []},
    )

    results = list(search_iterator)
    tile_to_find = "_NT_"
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
    
def available_data():
    time_interval = date.today() - timedelta(days = 3), date.today()
    search_iterator = catalog.search(
        DataCollection.SENTINEL3_OLCI, # DataCollection.SENTINEL3_OLCI, use this for other data 
        bbox=aoi_bbox,
        time=time_interval,
        fields={"include": ["id", "properties.datetime"], "exclude": []},
    )

    results = list(search_iterator)
    for element in results:
       print(element)
   
    
############################################### 
# Image output and operating area 
###############################################

current_date = date_chooser() # NEEDS fixing -> gives passage on tile 180 
print(f"Using: {current_date}")

def daily_images(update = True, cloud_filter= True, map = True): # **
  if update:
    cnt = 0
    for element in vals:
        request_sentinel(element, image_names[cnt],1,"2024-09-01", "2024-09-03") # change param to 1 to get most recent valid date (0 for chosen date) 
        cnt+=1
  if cloud_filter:
    cloud_mask()
  if map:
     land_mask()
     legends()
     
available_data() # for seeing available slots and debugging 
daily_images(True,True,True) # **
