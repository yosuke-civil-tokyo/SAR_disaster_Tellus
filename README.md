# Differential Interferometric SAR
## The first note
This repository is for obtaining a pair of SAR images from [Tellus API](https://www.tellusxdp.com/ja/api-reference/), and estimating road-areas effected by flood referring to [a paper](https://www.jstage.jst.go.jp/article/jscejsp/77/2/77_I_33/_article/-char/ja/) or [a report from NILIM](http://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1110pdf/ks1110_06.pdf)  
You need to run the part of searching and getting SAR images on the Tellus environment. (access through [here](https://www.tellusxdp.com/ja/))  
For data directory structure, check data/README.md

## Environment
Make a small environment for this project to run python files.  
You can just  

```
conda env create -f env.yml  
conda activate sar
```

## Obtain images
### Prerequisites
- Tellus API TOKEN
- Target region's [latitude, longitude]
- Target disaster's date

### flow
1. Search an interferometric pair of SAR images on your target region which include data on your target disaster's date. Take note of data pair's dataset_id you want to download.
    ```
    python search_sar.py [TOKEN] -p [L2.1] -s [search start date] -e [search end date] -lat [region's lat] -lon [region's lon]
    ```
    Check the interferometric pair exists.  
    For [search start date] and [search end date], use yyyy-mm-dd style. [search end date] may be set as one or two weeks later of your target disaster.  

2. Obtain the pair of images. Input the dataset_id you searched above.  
    ```
    python sar_tellus.py [TOKEN] [dataset_id] -p [L2.1] -print [True or False]
    ```
    Now ./data/raw_sar_L2/ includes downloaded SAR data.

## Extract damaged areas
### Prerequisites
- a pair of SAR image
- the target region (rectangle)
- the RGB tiff image (if you want to visualize on it)
- road data (if you aggregate results on road)

### flow
1. Run below (make sure you've already obtained image like above and 'data/raw_sar_L2' contains your data)

    ```
    python main.py -ulx [top left longutude] -uly [top left latitude] -lrx [bottom right longitude] -lry [bottom right longitude] -place [name your region] -road [your road data path] -overlay [your RGB image path]
    ```
    For road data, edge file (.csv) and road mask (.csv) are required.  
    Road data creation is from other repository forked from [SpaceNet](https://github.com/avanetten/cresi).