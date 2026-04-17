#!/usr/bin/env python
#
# Author: Shengtao Wang

import argparse
import os
import re
import time
import astropy.wcs as wcs
import numpy as np
from astropy.io import fits as pf
from astropy.wcs.utils import proj_plane_pixel_area

def parse_args():
    parser = argparse.ArgumentParser(description="Calculate integrated flux density from a FITS image and masks.")
    parser.add_argument("filename", help="FITS image filename, for example 'PN.i.image.fits'.")
    parser.add_argument("-p", "--percent", type=float, default=0.05, help="Relative calibration error, default=0.05.")
    parser.add_argument("--path", default=".", help="Directory containing the FITS file and mask files. Default: current directory.")
    return parser.parse_args()

def load_fits_image(filename):
    header = pf.getheader(filename)
    data = pf.getdata(filename)
    naxis = len(data.shape)

    if naxis == 2:
        xydata = data.copy()
    elif naxis == 3:
        xydata = data[0].copy()
    elif naxis == 4:
        xydata = data[0][0].copy()
    elif naxis == 5:
        xydata = data[0][0][0].copy()
    else:
        raise ValueError(f"Data array contains {naxis} axes; only up to 5 are supported.")

    strip_head_keys = ["NAXIS", "CRVAL", "CRPIX", "CDELT", "CTYPE", "CROTA", "CD1_", "CD2_", "CUNIT"]
    strip_head_keys1 = ["PC1_", "PC2_", "PC3_", "PC4_", "PC01_", "PC02_", "PC03_", "PC04_"]
    if naxis >= 3:
        for i in range(3, 6):
            for key in strip_head_keys:
                header_key = key + str(i)
                if header_key in header:
                    del header[header_key]
            for key in strip_head_keys1:
                for j in range(1, 6):
                    header_key = key + str(j)
                    if header_key in header:
                        del header[header_key]
        header["NAXIS"] = 2

    coord_type = None
    x_indx = None
    y_indx = None
    ra_regx = re.compile(r"^RA")
    dec_regx = re.compile(r"^DEC")
    glon_regx = re.compile(r"^GLON")
    glat_regx = re.compile(r"^GLAT")
    for i in range(int(header["NAXIS"])):
        keyword = "CTYPE" + str(i + 1)
        if ra_regx.match(header[keyword]):
            coord_type = "EQU"
            x_indx = i + 1
        if dec_regx.match(header[keyword]):
            y_indx = i + 1
        if glon_regx.match(header[keyword]):
            coord_type = "GAL"
            x_indx = i + 1
        if glat_regx.match(header[keyword]):
            y_indx = i + 1
    if not x_indx or not y_indx:
        raise ValueError("Failed to find Equatorial or Galactic axis coordinate types.")

    header["XINDEX"] = x_indx
    header["YINDEX"] = y_indx
    if coord_type:
        header["COORDSYS"] = coord_type

    try:
        header["BMAJ"] = header["CLEANBMJ"]
        header["BMIN"] = header["CLEANBMN"]
        header["BPA"] = header["CLEANBPA"]
    except Exception:
        pass

    try:
        xdelt = (-1) * (header["PIXSCAL" + str(x_indx)]) / 3600.0
        ydelt = header["PIXSCAL" + str(y_indx)] / 3600.0
        header["CDELT" + str(x_indx)] = xdelt
        header["CDELT" + str(y_indx)] = ydelt
    except Exception:
        pass
    return header, xydata


def main():
    args = parse_args()
    start_time = time.time()

    base_path = os.path.abspath(args.path)
    fits_filename = args.filename
    percent = args.percent

    if not fits_filename.lower().endswith(".fits"):
        raise ValueError("filename must be a FITS file name ending with '.fits'.")

    filename = fits_filename[:-5]
    fits_name = os.path.join(base_path, fits_filename)
    src_mask_fits_name = os.path.join(base_path, filename + ".mask_source.fits")
    bkg_mask_fits_name = os.path.join(base_path, filename + ".mask_bakg.fits")
    all_data_name = os.path.join(base_path, "all.data")
    int_flux_data_name = os.path.join(base_path, "IntFlux.data")

    header, xydata = load_fits_image(fits_name)

    if "BMAJ" not in header:
        print("Please provide beam information!")
        header["BMAJ"] = float(input("BMAJ in deg: "))
        header["BMIN"] = float(input("BMIN in deg: "))
        header["BPA"] = float(input("BPA in deg: "))

    w = wcs.WCS(header)
    w_cel = w.celestial if w.has_celestial else w

    if "BUNIT" in header:
        print("BUNIT:", header["BUNIT"])
    else:
        print("Warning: BUNIT not found in FITS header. This script assumes the image is in Jy/beam.")

    src_mask_fits = pf.getdata(src_mask_fits_name)
    bkg_mask_fits = pf.getdata(bkg_mask_fits_name)

    finite_mask = np.isfinite(xydata)
    src_select = finite_mask & (src_mask_fits >= 0.5)
    bkg_select = finite_mask & (bkg_mask_fits >= 0.5)

    num = int(np.count_nonzero(src_select))
    num_bkg = int(np.count_nonzero(bkg_select))
    if num == 0:
        raise ValueError("No valid pixels found in source mask.")
    if num_bkg < 2:
        raise ValueError("Not enough valid pixels found in background mask.")

    src_values = xydata[src_select]
    bkg_values = xydata[bkg_select]

    pixel_area_sr = proj_plane_pixel_area(w_cel) * (np.pi / 180.0) ** 2
    beam_area_sr = (np.pi * np.radians(header["BMAJ"]) * np.radians(header["BMIN"]) / (4.0 * np.log(2.0)))
    src_area_sr = num * pixel_area_sr
    bkg_area_sr = num_bkg * pixel_area_sr
    nsrc_beam = src_area_sr / beam_area_sr
    nbkg_beam = bkg_area_sr / beam_area_sr

    with open(all_data_name, "a+") as f1:
        print(file=f1)
        print(filename + ":", file=f1)
        print("total area (sr): ", src_area_sr, file=f1)
        print("total area (beam): ", nsrc_beam, file=f1)

    ave_bkg = float(np.mean(bkg_values))
    sigma = float(np.std(bkg_values, ddof=1))

    with open(all_data_name, "a+") as f1:
        print("bkg: ", ave_bkg, file=f1)
        print("rms: ", sigma, file=f1)

    sum_src = float(np.sum(src_values))
    int_flux = sum_src * pixel_area_sr / beam_area_sr
    int_flux_bg = float(np.sum(src_values - ave_bkg)) * pixel_area_sr / beam_area_sr

    sigma_n = sigma * np.sqrt(nsrc_beam + (nsrc_beam ** 2) / nbkg_beam)
    sigma_s = abs(int_flux_bg) * percent
    sigma_tot = np.sqrt(sigma_n ** 2 + sigma_s ** 2)

    print("Number of source pixels:", num)
    print("Number of background pixels:", num_bkg)
    print("N_src_beam:", nsrc_beam)
    print("N_bkg_beam:", nbkg_beam)
    print("Background level (Jy/beam):", ave_bkg)
    print("Background rms (Jy/beam):", sigma)
    print("Integrated flux before background subtraction (Jy):", int_flux)
    print("Integrated flux after background subtraction (Jy):", int_flux_bg)
    print("sigma_N (Jy):", sigma_n)
    print("sigma_S (Jy):", sigma_s)
    print("sigma_tot (Jy):", sigma_tot)

    with open(all_data_name, "a+") as f1:
        print("Number of points: ", num, file=f1)
        print("Number of background points: ", num_bkg, file=f1)
        print("N_src_beam: ", nsrc_beam, file=f1)
        print("N_bkg_beam: ", nbkg_beam, file=f1)

    with open(int_flux_data_name, "a+") as f:
        print(filename + ":", file=f)
        print("{0:<8.4f}{1:8.4f}{2:10.6f}{3:8.4f}".format(int_flux, int_flux_bg, sigma, sigma_tot), file=f)

    run_time = time.time() - start_time
    print("Run time is:", run_time)

if __name__ == "__main__":
    main()
