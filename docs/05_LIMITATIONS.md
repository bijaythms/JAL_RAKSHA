# Consolidated Limitations Register

The platform contract: every limitation is (a) printed next to the numbers
it affects, (b) aggregated into every report, (c) listed here.

1. Breach: empirical equations trained on embankment dams; natural dams out
   of domain. k_d/tau_c are literature orders of magnitude, not lab values.
2. Routing: 1D, single centerline, corridor envelope; no 2D SWE, no
   backwater, no debris bulking (debris fronts can be ~10x more
   destructive than the clear-water model).
3. Detection: threshold water mapping (no shadow masking - mountain
   shadows cause false positives without an ROI); revisit-bound (5-12 d);
   mixed-sensor baseline bias (optical-dry baseline vs SAR current).
4. DEM: GLO-30 is 30 m and 2011-2015 era - depth/volume valid only for
   lakes newer than the DEM.
5. Impacts: regional damage curves; point-sampled agriculture; PLACEHOLDER
   unit costs until district SSR replacement.
6. Evacuation: walking lower bound; no roads/traffic/vulnerable-population
   fractions; RED means "walking infeasible" (vertical doctrine).
7. Regions: 8 physiographic presets are order-of-magnitude, not site
   calibrations; boundary cities may misclassify (override endpoint
   provided).
8. Growth alerts: advisory heuristics, not a learned classifier; snow
   season can fake DRAINING.
9. Non-erodible dams: overtopping-only paradigm; monolith stability not
   modeled - engineered structures need their own PMF/EAP studies.
