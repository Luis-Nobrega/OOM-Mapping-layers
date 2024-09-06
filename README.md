# Automatic image generation for layers of sentinel satellites 2 and 3 
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
It allows satellite images to be retrieved from Sentinel 2 and Sentinel 3. Processes irradiance bands to create images according to [Copernicus Browser](https://browser.dataspace.copernicus.eu) or referenced *academic papers*, when layers are L2 instead of L1.

## Needed packages 
Prior to running some packages have to be installed:
```
pip install matplotlib pandas getpass sentinelhub oauthlib requests_oauthlib datetime PIL numpy 
```

## Running 

Change `client_id` and `client_secret` to your personal tokens provided by [copernicus.eu](https://browser.dataspace.copernicus.eu). For information about getting these tokens: [secret_tokes](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html); [FAQ's](https://documentation.dataspace.copernicus.eu/FAQ.html).

### Running For the first time 
After installing Sentinelhub, it is necessary to configure it for the first time before running. For that, all it takes is to **uncomment**:

```
config = SHConfig()
config.sh_client_id = client_id
config.sh_client_secret = client_secret
config.sh_base_url = 'https://sh.dataspace.copernicus.eu'
config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
config.save("cdse")
```
And run one of the scripts normally.

### Repeated runnings

The above lines can be commented on for the remaining times, as reconfiguring the sentinel hub several times may slow down the image generation.

If for some reason, another setup is done, or the access tokens do not work, run it as if it were the first time.

### Token validity

By default, *Copernicus.eu* tokens tend to last 3 months. Asking for a permanent token is possible, but always a risk. Please consider using a token with a validy of 1-2 years instead.

## Periodic running 
If you desire to run both (or more) files at once automatically, [runner.py](/runner.py) has `single_run()`, `permanent_run()` and `run_at_hour()` ready. While the first one only runs it once, the second one runs it based on a time interval (ex:12h) and the third one runs it at the same hour, every day.

As it occupies the console, it is recommended to run it in the background, on a server that is always running:

```
python3 runner.py &
```

## Changing dates 
By default, the program will try to find the most recent layer based on the sentinel requests and IDs provided. This sometimes may wrongfully give you a date that is 1-2 days delayed.

To manually choose dates, change the `request_sentinel(element, image_names[cnt],1, "2024-09-01", "2024-09-03")` to have the appropriate date and to have a `0` as an input parameter.

If automatic dates are being used, to be 100% sure that the date corresponds to the current day, don't alter `request_sentinel(...)` and instead comment on the line that says `current_date = date_chooser()`. This action may, however, return you an image with passages from two different days.

## Altering the files
### Adding more layers
The script is malleable and prone to the addition of more imaging layers. Just add a new variable, for example:
```
evalscript_sentinel3_olci_Tristimulus = """
//VERSION=3
function evaluatePixel(samples) {
	let red = Math.log(1.0 + 0.01 * samples.B01 + 0.09 * samples.B02+ 0.35 * samples.B03 + 0.04 * samples.B04 + 0.01 * samples.B05 + 0.59 * samples.B06 + 0.85 * samples.B07 + 0.12 * samples.B08 + 0.07 * samples.B09 + 0.04 * samples.B10);
	let green= Math.log(1.0 + 0.26 * samples.B03 + 0.21 *samples.B04 + 0.50 * samples.B05 + samples.B06 + 0.38 * samples.B07 + 0.04 * samples.B08 + 0.03 * samples.B09 + 0.02 * samples.B10);
	let blue= Math.log(1.0 + 0.07 * samples.B01 + 0.28 * samples.B02 + 1.77 * samples.B03 + 0.47 * samples.B04 + 0.16 * samples.B05);
	return [red, green, blue, samples.dataMask];
}

function setup() {
 return {
   input: [ "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "dataMask"],
   output: { bands: 4},
 }
}
```

This code comes in **JSON** format and can be easily edited with **AI** tools or through [here](https://forum.sentinel-hub.com/t/working-with-json-responses-sentinel-hub/6905/3). For readily available code, look for **</>** in [copernicus browser](https://browser.dataspace.copernicus.eu).

Watchout for the provided band. Ex: While all **OLCI** bands are supported, sentinel3 **SLSTR** would require modifications to [copernicusS3_updated.py](/copernicusS3_updated.py).

Right [now](https://sentinelhub-py.readthedocs.io/en/latest/examples/process_request.html) (04/09/2024) they are:
```
DataCollection.SENTINEL2_L1C
DataCollection.SENTINEL2_L2A
DataCollection.SENTINEL1
DataCollection.SENTINEL1_IW
DataCollection.SENTINEL1_IW_ASC
DataCollection.SENTINEL1_IW_DES
DataCollection.SENTINEL1_EW
DataCollection.SENTINEL1_EW_ASC
DataCollection.SENTINEL1_EW_DES
DataCollection.SENTINEL1_EW_SH
DataCollection.SENTINEL1_EW_SH_ASC
DataCollection.SENTINEL1_EW_SH_DES
DataCollection.DEM
DataCollection.DEM_MAPZEN
DataCollection.DEM_COPERNICUS_30
DataCollection.DEM_COPERNICUS_90
DataCollection.MODIS
DataCollection.LANDSAT_MSS_L1
DataCollection.LANDSAT_TM_L1
DataCollection.LANDSAT_TM_L2
DataCollection.LANDSAT_ETM_L1
DataCollection.LANDSAT_ETM_L2
DataCollection.LANDSAT_OT_L1
DataCollection.LANDSAT_OT_L2
DataCollection.SENTINEL5P
DataCollection.SENTINEL3_OLCI
DataCollection.SENTINEL3_SLSTR
```

Other necessary changes are below:

### Adding a new satellite/layer

To add a new satellite or layer, a new file can either be created and the  `request_sentinel(...)` function altered or a new function can be added to an existing file:
```
data_collection=DataCollection.SENTINEL3_SLSTR.define_from
```
After that and adding the layer that stores the **JSON**, `vals` `image_names` and `units` variables must be altered to contain new layers and remove the unnecessary layers. 

There is also an `excluded` variable that stores special layers that either don't need cloud or land maskings or are used to generate those masks. It is not recommended to alter that. 

For example, to use a cloud mask, with an image that requires **SLSTR** it is recommended to add a new `request_sentinel()` function, as the cloud mask comes from the **RGB** layer in **OLCI**.

For new layers without masks, it is recommended to base new files on [copernicusS2.py](/copernicusS2.py), as it treats raw images.

## Box and resolution 
To change the area of interest, alter these coordinates. It should ideally be a [box](http://bboxfinder.com/). 
```
aoi_coords_wgs84 = [-17.567139,32.296420,-16.040039,33.312168] 
resolution = 60 
```
If there is a problem with resolution, something as:
```
Max allowed value for an image is 2894
```
Increase the resolution value. It isn't really the image resolution in meters, just a parameter to adjust the **JPEG** file. The true resolutions can be found in [ESA](https://sentiwiki.copernicus.eu/web/sentiwiki).

## Cloud mask regards
The cloud mask was built based on RBG images, as the sum of the values in the pixels tends to be higher in clouds. As of now it is set to **180**, but some thinner clouds might escape. 

To be more precise, reduce the value (maybe to 160-170) but be careful as this might also start blocking land areas.

## Land mask and labels
These are done separately and require fine-tuning.
Given the data format (RGB) and not intensity, the label had to be added as a separate **JPEG** in the "jet" colour scale. If your land filter takes too long or seems corrupted, adding [premade colourbar](/images/colorbar_only.jpeg) prior to running, may speed up of fix the problem.

For more info, email one of the contributors at OOM/ARDITI.

## Sentinel 2 images
True Colour image
![image](/images/TRUE_COL2.jpeg)
Short wave infrared (SWIR)
![image](/images/SWIR2.jpeg)
Normalized Difference Water Index (NDWI)
![image](/images/NDWI2.jpeg)
## Sentinel 3 images 
RGB 
![image](/images/RGB.jpeg)
Terrestrial Chlorophyll Index
![image](/images/OTCI.jpeg)
Integrated Water Vapour (IWV) - [source](https://earth.esa.int/eogateway/documents/20142/37627/cawa-algorithm-theoretical-basis-water-vapor.pdf) 
![image](/images/IWV.jpeg)
Algal pigment concentration (open waters) - [source](http://www.jeeng.net/pdf-152428-77647?filename=The%20Interaction%20of.pdf)
![image](/images/CHL.jpeg) 
Aerosol Angstrom exponent - [source](https://instesre.org/Aerosols/angstrom.htm)
![image](/images/AAE.jpeg)
Total suspended matter (TSM)
![image](/images/TSM.jpeg)

## Credits

Made by:
- Luís Fernando Nóbrega 
- Jesus Reis 

Thank you to:
- Rui Vieira for the land mask
- Ricardo Faria 
