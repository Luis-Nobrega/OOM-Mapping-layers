# OOM-Mapping-layers
Provides meteorological maps based on Sentinel 2 and 3 satellite imagery 

## Motivation
Adding new layers for [OOM website](https://oom.arditi.pt/index.php), especially the [satellite imagery section](https://oom.arditi.pt/index.php?page=satellite).
![image](https://oom.arditi.pt/assets/OOM_Logo.png)
## Tech/framework used
<b>Built with</b>
- [Pyhton](https://www.python.org/)
- [Sentinel hub](https://www.sentinel-hub.com/)
- [Copernicus Browser](https://browser.dataspace.copernicus.eu)

## Features
Allows to get satellite images from Sentinel2 and Sentinel3. Processes irradiance bands to create images according to [Copernicus Browser](https://browser.dataspace.copernicus.eu) or referenced academic papers, when layers are L2 instead of L1.

## Needed packages 

## Running 

Change `client_id` and `client_secret` to your personal tokens provided by [copernicus.eu](https://browser.dataspace.copernicus.eu). For information about getting this tokens: [secret_tokes](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html); [FAQ's](https://documentation.dataspace.copernicus.eu/FAQ.html).

### For the first time 

### Other times

## Changing dates 
By default, the program will try to find the most recent layer based on the sentinel requests and ID's provided. This sometimes may wrongfully give you a date that is 1-2 days delayd. 

To manually choose dates, change the `request_sentinel(element, image_names[cnt],1,"2024-09-01", "2024-09-03")` to have the apropriate date and to have a `0`.

To be 100% sure that the date corresponds to current day, don't alter `request_sentinel(...)` and instead comment the line that says `current_date = date_chooser()`.

## Adding more layers

## Sentinel 2 images
True Colour image
![image](/images/TRUE_COL2.jpeg)
Short wave infrared (SWIR)
![image](/images/SWIR2.jpeg)
Normalized Difference Water Index (NDWI)
![image](/images/NDWI2.jpeg)
RGB 
## Sentinel 3 images 
![image](/images/RGB.jpeg)
Terrestrial Chlorophyll Index
![image](/images/OTCI.jpeg)
Integrated Water Vapour
![image](/images/IWV.jpeg)
Algal pigment concentration (open waters)
![image](/images/CHL.jpeg)
Aerosol Angstrom exponent
![image](/images/AAE.jpeg)
Total suspended matter (TSM)
![image](/images/TSM.jpeg)
