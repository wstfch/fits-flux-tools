# fits-flux-tools

Small command-line tools for measuring integrated flux density from FITS images.

## Tools

- `polymask`: open a FITS image, draw source/background polygons, and save DS9 region files plus FITS masks
- `cal-int-flux-density`: calculate integrated flux density and uncertainty from a FITS image and the saved masks

## Installation

```bash
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

