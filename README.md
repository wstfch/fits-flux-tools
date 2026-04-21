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
fits-flux-tools --help
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

### Package metadata

After installation, you can inspect the package metadata from the top-level CLI:

```bash
fits-flux-tools --help
fits-flux-tools --version
```

### 1. Create masks:
Example:
```bash
polymask NGC253.i.image.fits
polymask NGC253.i.image.fits --save_reg
polymask NGC253.i.image.fits --rms 0.000016 --t_rms 5 --save_reg
```
Note: When running polymask, you can adjust the color scale by clicking on the
  color bar. First, outline the target source, then click Save Source. Next, click
  Reset, select a background region free of bright sources, and click Save
  Background.

Output files:
    Save Source:
      <name>.mask_source.fits
      and, if --save_reg is set:
      <name>.mask.source.image.reg
      <name>.mask.source.fk5.reg  or  <name>.mask.source.galactic.reg

    Save Background:
      <name>.mask_bakg.fits
      and, if --save_reg is set:
      <name>.mask.bakg.image.reg
      <name>.mask.bakg.fk5.reg  or  <name>.mask.bakg.galactic.reg

### 2. Measure integrated flux density in the current directory:

```bash
cal-int-flux-density NGC253.i.image.fits
```

Measure with explicit calibration error, path, source-mask and background-mask:

```bash
cal-int-flux-density NGC253.i.image.fits --percent 0.1 --path /path/to/data -s /path/to/data/NGC253.i.image.mask_source.fits -b /path/to/data/NGC253.i.image.mask_bakg.fits
```

## Expected Files

Output files are written to the selected `--path` directory:

- `all.data`
- `IntFlux.data`  
Note: In 'IntFlux.data', the first and second columns are the integrated flux densities before and after background subtraction, respectively. The third column gives the local image rms measured from the background region, and the fourth column gives the total uncertainty, including both the relative calibration uncertainty and the image-noise term.
