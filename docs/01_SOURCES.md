# Scientific Sources & Model Provenance

Items marked [VERIFY] should be re-checked against primary literature
before operational deployment.

## Breach hydraulics
- Kirkpatrick (1977), "Evaluation of dam failures caused by overtopping" - ensemble member
- SCS (1981), USDA SCS draft report - ensemble member
- USBR (1981), "Guidelines for defining inundation areas" - ensemble member
- Froehlich (1995), J. Water Res. Planning Mgmt 121(1): Qp=0.607 Vw^0.295 Hw^1.24;
  B=0.1803 k_o Vw^0.32 Hb^0.04 (k_o 1.4 overtop / 1.0 piping)
- Froehlich (2008), J. Hyd. Eng. 134(12): t_f = 63.2 sqrt(Vw/(g Hb^2))
- Von Thun & Gillette (1990), USBR Guidelines: t_f = 0.015 Hb (erodible) / 0.02 Hb + 0.25
- Wahl (1998, 2004), USBR Dam Safety Tech. Reports - ensemble compilation
- Hanson & Temple (1997), erosion of earthen channels/dams: dz/dt = k_d(tau-tau_c)
  [VERIFY class values of k_d, tau_c]

## Flood routing
- Muskingum-Cunge: Cunge, J.A. (1969), J. Hydraulics Div. ASCE 95(HY6).
  K = dx/c; X = 0.5(1 - q0/(S0 c B dx))
- Manning normal depth (wide channel): Chow (1959), Open-Channel Hydraulics

## Inflow hydrology
- SCS Curve Number: NRCS NEH-4 (1972) / NEH Part 630 (2004) Ch. 9-11
- SCS triangular unit hydrograph: NEH-4 Ch. 16 [VERIFY regional Tc methods]
- Degree-day snowmelt: Hock, R. (2003), J. Hydrology 282; DDF values per
  Zhang et al. (2006), Annals of Glaciology 43 [VERIFY per facies]

## Remote sensing
- MNDWI: Xu, H. (2006), Int. J. Remote Sensing 27(14)
- NDWI: McFeeters, S.K. (1996), Int. J. Remote Sensing 17(7)
- SAR water threshold (sigma0 < -17 dB): operational practice [VERIFY per calibration]
- Data: Copernicus Data Space Ecosystem (S1 GRD, S2 L2A, GLO-30 DEM);
  USGS Landsat C2 L2 (LandsatLook STAC) and NWIS IV

## Hazard & damage
- People hazard d*v thresholds (0.5/1.2/2.0 m2/s): DEFRA/EA FD2320
  "Flood Risks to People" (2005/2006); ARR Book 6 (2019)
- Building depth-damage: Huizinga, J. et al. (2017), JRC Technical Report
  "Global flood depth-damage functions" (Asia residential)
- Agriculture loss: FAO damage-assessment frameworks [PLACEHOLDER unit costs]

## Risk index
- TDRI weights are PLATFORM-DEFINED multi-criteria weights, documented in
  assessment.py and sensitivity-tested +/-20% one-at-a-time. Not an external standard.

## Geodesy
- Haversine/destination formulas: standard spherical geodesy
