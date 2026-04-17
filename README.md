# fits-flux-tools

Small command-line tools for measuring integrated flux density from FITS images.

## Tools

- `polymask`: open a FITS image, draw source/background polygons, and save DS9 region files plus FITS masks
- `cal-int-flux-density`: calculate integrated flux density and uncertainty from a FITS image and the saved masks

## Installation

```bash
git clone https://github.com/wstfch/fits-flux-tools.git
cd fits-flux-tools
pip install .
```

## Uninstall

```bash
pip uninstall fits-flux-tools
```

## Dependencies

- `numpy`
- `astropy`
- `matplotlib`
- `sphericalpolygon`
- a Qt backend for Matplotlib when using `polymask`

## Usage

Create masks:

```bash
polymask NGC253.i.image.fits
```
Note: When running polymask, you can adjust the color scale by clicking on the color bar. First, outline the target source, then click Mask and Save. After that, click Reset, select a background region free of bright sources, then click Mask and Save again.

Measure integrated flux density in the current directory:

```bash
cal-int-flux-density NGC253.i.image.fits
```

Measure with explicit calibration error and path:

```bash
cal-int-flux-density NGC253.i.image.fits --percent 0.02 --path /path/to/data
```

## Expected Files

For an input image `NGC253.i.image.fits`, `cal-int-flux-density` expects:

- `NGC253.i.image.mask.source.fk5.reg`
- `NGC253.i.image.mask.bakg.fk5.reg`
- `NGC253.i.image.mask_source.fits`
- `NGC253.i.image.mask_bakg.fits`

Output files are written to the selected `--path` directory:

- `all.data`
- `IntFlux.data`  
Note: The first and second columns are the integrated flux densities before and after background-noise subtraction, respectively. The third column gives the background noise, and the fourth column gives the uncertainty, including both the telescope’s relative calibration uncertainty and the image rms noise.

