#!/usr/bin/env python
#
# Author: Shengtao Wang

import argparse
import os
import re
import sys
import time

import astropy.wcs as wcs
import numpy as np
from astropy import units as u
from astropy.io import fits as pf
from sphericalpolygon import Sphericalpolygon


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calculate integrated flux density from a FITS image and masks."
    )
    parser.add_argument(
        "filename",
        help="FITS image filename, for example 'PN.i.image.fits'.",
    )
    parser.add_argument(
        "-p",
        "--percent",
        type=float,
        default=0.05,
        help="Relative calibration error, for example 0.02.",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Directory containing the FITS file and mask files. Default: current directory.",
    )
    return parser.parse_args()


def polygon_line_to_list(line):
    match = re.search(r"polygon\s*\((.*?)\)", line, re.IGNORECASE)
    if not match:
        raise ValueError("No polygon(...) definition found in region file.")
    return np.array([float(value) for value in match.group(1).split(",")])


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

    strip_head_keys = [
        "NAXIS",
        "CRVAL",
        "CRPIX",
        "CDELT",
        "CTYPE",
        "CROTA",
        "CD1_",
        "CD2_",
        "CUNIT",
        "PC1_",
        "PC2_",
        "PC3_",
        "PC4_",
    ]
    strip_head_keys1 = [
        "PC1_",
        "PC2_",
        "PC3_",
        "PC4_",
        "PC01_",
        "PC02_",
        "PC03_",
        "PC04_",
    ]
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
    src_mask_name = os.path.join(base_path, filename + ".mask.source.fk5.reg")
    bkg_mask_name = os.path.join(base_path, filename + ".mask.bakg.fk5.reg")
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

    src_mask_fits = pf.getdata(src_mask_fits_name)
    bkg_mask_fits = pf.getdata(bkg_mask_fits_name)

    with open(src_mask_name, "r") as f:
        src_line = next(ln for ln in f if "polygon" in ln.lower())
    src_mask = polygon_line_to_list(src_line)

    with open(bkg_mask_name, "r") as f:
        bkg_line = next(ln for ln in f if "polygon" in ln.lower())
    bkg_mask = polygon_line_to_list(bkg_line)

    src_mask = np.reshape(np.flip(src_mask), (src_mask.size // 2, 2))
    bkg_mask = np.reshape(np.flip(bkg_mask), (bkg_mask.size // 2, 2))

    polygon_src = Sphericalpolygon.from_array(src_mask * u.deg)
    polygon_bkg = Sphericalpolygon.from_array(bkg_mask * u.deg)

    m_size, n_size = xydata.shape

    with open(all_data_name, "a+") as f1:
        print(file=f1)
        print(filename + ":", file=f1)
        print("total area: ", polygon_src.area(), file=f1)

    num_bkg = 0
    tot_bkg = 0.0
    tot_bkg2 = 0.0
    for i in range(m_size):
        for j in range(n_size):
            if np.isnan(xydata[i, j]):
                continue
            if bkg_mask_fits[i, j] < 0.5:
                continue
            x = w.wcs_pix2world([(j, i)], 0)
            ra = x[0][0]
            dec = x[0][1]
            if polygon_bkg.contains_points([dec, ra]):
                tot_bkg += xydata[i, j]
                tot_bkg2 += xydata[i, j] * xydata[i, j]
                num_bkg += 1

    ave_bkg = tot_bkg / num_bkg
    rms = np.sqrt(tot_bkg2 / num_bkg - ave_bkg * ave_bkg)

    with open(all_data_name, "a+") as f1:
        print("bkg: ", ave_bkg, file=f1)
        print("rms: ", rms, file=f1)

    num = 0
    tot_flux = 0.0
    tot_flux_bkg = 0.0
    for i in range(m_size):
        for j in range(n_size):
            if np.isnan(xydata[i, j]):
                continue
            if src_mask_fits[i, j] < 0.5:
                continue
            x = w.wcs_pix2world([(j, i)], 0)
            ra = x[0][0]
            dec = x[0][1]
            if polygon_src.contains_points([dec, ra]):
                tot_flux += xydata[i, j]
                tot_flux_bkg += xydata[i, j] - ave_bkg
                num += 1

    beam_norm = 1.13 * np.radians(header["BMAJ"]) * np.radians(header["BMIN"])
    int_flux = tot_flux * ((polygon_src.area() / num) / beam_norm)
    int_flux_bg = tot_flux_bkg * ((polygon_src.area() / num) / beam_norm)

    beam_area = np.pi * np.radians(header["BMAJ"]) * np.radians(header["BMIN"])
    n_num_indep = polygon_src.area() / beam_area
    print("N_num:", n_num_indep)

    p_mu2_sum = 0.0
    for i in range(m_size):
        for j in range(n_size):
            if np.isnan(xydata[i, j]):
                continue
            if bkg_mask_fits[i, j] < 0.5:
                continue
            x = w.wcs_pix2world([(j, i)], 0)
            ra = x[0][0]
            dec = x[0][1]
            if polygon_bkg.contains_points([dec, ra]):
                p_mu2_sum += (xydata[i, j] - ave_bkg) ** 2

    sigma = np.sqrt(p_mu2_sum / num_bkg)
    print("sigma:", sigma)
    sigma_n = sigma * np.sqrt(n_num_indep)
    print("sigma_N:", sigma_n)
    sigma_s = int_flux * percent
    print("sigma_S:", sigma_s)
    sigma_tot = np.sqrt(sigma_n ** 2 + sigma_s ** 2)

    with open(all_data_name, "a+") as f1:
        print("Number of points: ", num, file=f1)

    with open(int_flux_data_name, "a+") as f:
        print(filename + ":", file=f)
        print(
            "{0:<8.4f}{1:8.4f}{2:10.6f}{3:8.4f}".format(
                int_flux, int_flux_bg, sigma, sigma_tot
            ),
            file=f,
        )

    run_time = time.time() - start_time
    print("Run time is:", run_time)


if __name__ == "__main__":
    main()
