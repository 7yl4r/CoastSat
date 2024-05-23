# 1. Initial settings

# load modules
import os
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec

matplotlib.use("Qt5Agg")

plt.ion()

from coastsat import (
    SDS_download,
    #SDS_no_clouds,
    SDS_preprocess,
    SDS_shoreline,
    SDS_tools,
)

from coregistration import coregister

# outputs path

output_dir = Path("01_OUTPUTS/")

# options
download_images = False
coregister_images = True

# region of interest (longitude, latitude in WGS84)

np.seterr(divide='ignore', invalid='ignore')


#TODO: Cargar una gpkg con los tramos
#Para cada tramo
#Calcular el rectángulo paralelo a los ejes que lo incluye

tramo = "G03_03"

if tramo == "G03_01":  #  G02_01 (Playa Cantarriján - Marina del Este)

    polygon = [
        [
            [-3.4226, 36.7571],
            [-3.4226, 36.6948],
            [-3.2973, 36.6948],
            [-3.2973, 36.7571],
        ]
    ]

elif tramo == "G03_02":  ## G02_02 - Peñón Salobreña - Pto. Motril
    polygon = [
        [
            [-3.3119, 36.7626],
            [-3.3119, 36.7324],
            [-3.2074, 36.7324],
            [-3.2074, 36.7626],
        ]
    ]

elif tramo == "G03_03":  ## G02_03 - Pto. Motril - Pta de Cerro Gordo
    polygon = [
        [
            [-3.3119, 36.7626],
            [-3.3119, 36.7324],
            [-3.1000, 36.7324],
            [-3.1000, 36.7626],
        ]
    ]

# Guadalfeo - Pta Santo
# polygon = [[[-3.5765, 36.7262],
#            [-3.5765, 36.7130],
#            [-3.5487, 36.7130],
#            [-3.5487, 36.7262],
#            ]]

# date range
dates = ["2008-01-01", "2015-06-30"]

# satellite missions
sat_list = ["L7"]

# name of the site
foldersite = "L7_2008_2015"
sitename = tramo

# filepath where data will be stored
# filepath_data = os.path.join(os.getcwd(), foldersite)
filepath_data = Path(f"{output_dir}/{foldersite}")

# put all the inputs into a dictionnary
inputs = {
    "polygon": polygon,
    "dates": dates,
    "sat_list": sat_list,
    "sitename": sitename,
    "filepath": filepath_data,
    "landsat_collection": "C02"
}

# before downloading the images, check how many images are available for your inputs
if 1:
    SDS_download.check_images_available(inputs)

# 2. Retrieve images

# retrieve satellite images from GEE
if download_images:
    metadata = SDS_download.retrieve_images(inputs)


# 2.5 Coregistration
if coregister_images:
    for sat in sat_list:
        coregister(output_dir, foldersite, sitename, sat)


# if you have already downloaded the images, just load the metadata file
metadata = SDS_download.get_metadata(inputs)

# 3. Batch shoreline detection

settings = {
    # general parameters:
    "cloud_thresh": 0.05,  # threshold on maximum cloud cover
    "output_epsg": 25830,  # epsg code of spatial reference system desired for the output
    # quality control:
    # - 'check_detection' shows each shoreline detection to the user for validation
    # - 'adjust_detection' allows user to adjust the postion of each shoreline by
    # changing the threhold
    # - 'save_figure' saves a figure showing the mapped shoreline for each image
    "check_detection": True,
    "adjust_detection": True,
    "save_figure": True,
    # add the inputs defined previously
    "inputs": inputs,
    # [ONLY FOR ADVANCED USERS] shoreline detection parameters:
    # - 'min_beach_area': minimum area (in metres^2) for an object to be labelled
    # as a beach
    # - 'buffer_size': radius (in metres) of the buffer around sandy pixels considered
    # in the shoreline detection
    # - 'min_length_sl': minimum length (in metres) of shoreline perimeter to be valid
    # - 'cloud_mask_issue': switch this parameter to True if sand pixels are masked
    # (in black) on many images
    # - 'sand_color': 'default', 'dark' (for grey/black sand beaches) or 'bright'
    # (for white sand beaches)
    "min_beach_area": 4500,
    "buffer_size": 100,
    "min_length_sl": 200,
    "cloud_mask_issue": False,
    "sand_color": "dark",
}


# settings for the shoreline extraction

# [OPTIONAL] preprocess images (cloud masking, pansharpening/down-sampling)
SDS_preprocess.save_jpg(metadata, settings)

# [OPTIONAL] create a reference shoreline
# (helps to identify outliers andfalse detections)
settings["reference_shoreline"] = SDS_preprocess.get_reference_sl(metadata, settings)
# set the max distance (in meters) allowed from the reference shoreline
# for a detected shoreline to be valid
settings["max_dist_ref"] = 100

# extract shorelines from all images (also saves output.pkl and shorelines.kml)
output = SDS_shoreline.extract_shorelines(metadata, settings)

# remove duplicates (images taken on the same date by the same satellite)
output = SDS_tools.remove_duplicates(output)
# remove inaccurate georeferencing (set threshold to 10 m)
output = SDS_tools.remove_inaccurate_georef(output, 10)

# for GIS applications, save output into a GEOJSON layer
geomtype = "lines"  # choose 'points' or 'lines' for the layer geometry
gdf = SDS_tools.output_to_gdf(output, geomtype)
gdf.crs = {"init": "epsg:" + str(settings["output_epsg"])}  # set layer projection
# save GEOJSON layer to file
gdf.to_file(
    os.path.join(
        inputs["filepath"],
        inputs["sitename"],
        "%s_output_%s.geojson" % (sitename, geomtype),
    ),
    driver="GeoJSON",
    encoding="utf-8",
)
gdf.to_csv(os.path.join(inputs["filepath"], inputs["sitename"], "%s.csv" % sitename))

# plot the mapped shorelines
fig = plt.figure(figsize=[15, 8], tight_layout=True)
plt.axis("equal")
plt.xlabel("Eastings")
plt.ylabel("Northings")
plt.grid(linestyle=":", color="0.5")
for i in range(len(output["shorelines"])):
    sl = output["shorelines"][i]
    date = output["dates"][i]
    plt.plot(sl[:, 0], sl[:, 1], ".", label=date.strftime("%d-%m-%Y"))
plt.legend()


plt.savefig(os.path.join(inputs["filepath"], inputs["sitename"], "%s.pdf" % sitename))

# plt.show(block=True)
