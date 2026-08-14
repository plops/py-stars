The primary Wide camera on the iPhone 11
has a 26mm equivalent focal length, which corresponds to a field of view (FOV) of approximately 84 deg

To capture a full
spherical view using the primary Wide camera of an iPhone 11
, you will need a theoretical minimum of 12 images without overlap, or a practical total of 24 images when accounting for the mandatory overlap required to stitch the panorama.
Lens Specifications Breakdown
The iPhone 11 sensor utilizes a native 4:3 aspect ratio. Given its
diagonal field of view (FOV), the sensor yields the following dimensions: 

    Horizontal FOV (Landscape):
    Vertical FOV (Landscape):

1. Theoretical Minimum (12 Images)
The surface area of a full sphere measures exactly
steradians (approx. 12.57).

    A single frame from this lens covers 1.126 steradians of solid angle.
    Dividing the full sphere by the area of one frame (
    ) results in 11.16.
    This dictates an absolute geometric minimum of 12 photos if they could be tiled perfectly with zero gaps or overlaps.

2. Practical Stitching Reality (24 Images)
Panorama software requires a
to
overlap between adjacent photos to correctly align matching reference points. To maximize vertical resolution, stitching is typically shot in Portrait orientation (where width FOV becomes
and height FOV becomes
).
A standard multi-row panoramic head routine with a
safety overlap requires a 3-row layout plus poles:

    Middle Row (
    Pitch): 10 images rotated horizontally.
    Upper Row (
    Pitch): 6 images angled upward.
    Lower Row (
    Pitch): 6 images angled downward.
    Zenith (
    Sky): 1 image straight up.
    Nadir (
    Ground): 1 image straight down.
    Total Practical Portfolio: 24 images.


To determine the exact direction an iPhone camera is looking using stars (a process known as plate solving), a minimum of 3 stars must be detected in the image. However, to reliably match those stars against a database without false positives, your system will practically need to look for patterns containing 4 to 5 stars per field of view. [1] 
Here is the technical breakdown of how to structure your database and algorithm for an iPhone 11 Wide camera ($71.5^\circ \times 56.8^\circ$ landscape field of view).
------------------------------
## 1. Geometric Requirements (The Minimums)

* 3 Stars (Mathematical Minimum): Three stars form a triangle. The internal angles and side lengths (angular distances) provide enough geometric constraints to calculate the camera's pointing direction (Right Ascension and Declination) and rotation (roll). [2, 3] 
* 4–5 Stars (Practical Minimum): Real images contain sensor noise, hot pixels, or satellites. Algorithms like Lost-In-Space (LIS) star identification use 4-star combinations (quads) or 5-star combinations (pyramids) to drastically reduce false matches and handle noise. [4] 

------------------------------
## 2. Camera Field of View vs. Star Density
Because the iPhone 11 Wide lens has an exceptionally large field of view ($\approx 71^\circ$ wide), it sees a massive patch of the sky at once.

* Limiting Magnitude: From a dark sky site, an iPhone 11 exposure can easily capture stars down to Magnitude 5 or 6.
* Total Stars available: There are only about 5,000 to 9,000 stars in the entire night sky visible to the naked eye (up to Magnitude 6.5).
* Stars per frame: With a $71^\circ \times 56.8^\circ$ view, your camera covers roughly 10% of the entire sky in a single shot. This means even a sparse database of the brightest stars will yield dozens of stars in every single photo.

------------------------------
## 3. How to Build Your Database (The Table Structure)
You do not need massive professional catalogs like Gaia (billions of stars). Instead, use the Yale Bright Star Catalogue (BSC5) or the Hipparcos Catalogue, filtered only for stars brighter than magnitude 5.5 or 6.0. [5, 6] 
Your database pipeline should look like this:
## Table 1: Star Catalog (The Reference Nodes)

| Column Name | Data Type | Description |
|---|---|---|
| star_id | Integer (Primary Key) | Unique identifier (e.g., HR/Hipparcos number). |
| ra | Float | Right Ascension in degrees (0 to 360). |
| dec | Float | Declination in degrees (-90 to +90). |
| magnitude | Float | Apparent brightness (lower = brighter). |

## Table 2: The Feature Index (The Solving Table)
To make the search instantaneous, you should pre-calculate star patterns. For a wide-field iPhone lens, a Triangle (Triad) or Quad index works best. You index them by sorted angular distances or hash values. [7] 

| Column Name | Data Type | Description |
|---|---|---|
| hash_key | String / BigInt | A quantized index of the internal shapes/angles. |
| star_a | Integer | Foreign key to Table 1. |
| star_b | Integer | Foreign key to Table 1. |
| star_c | Integer | Foreign key to Table 1. |
| dist_ab | Float | Angular distance between A and B (in degrees). |
| dist_bc | Float | Angular distance between B and C (in degrees). |
| dist_ca | Float | Angular distance between C and A (in degrees). |

------------------------------
## 4. Recommended Solving Algorithms
Since you are developing this yourself, look into these open-source logic paths rather than writing the matrix math from scratch:

* Tetra: An incredibly fast, modern, lost-in-space star identification algorithm that uses 4-star combinations. It is ideal for custom databases. [8, 9, 10] 
* Astrometry.net Geometric Hashing: They use "quads" (groups of 4 stars) and scale-invariant hashes. Because your iPhone lens focal length is fixed and known (26mm equiv.), you can skip the scale-search step, making your local solver 100x faster than Astrometry.net. [11] 

Would you like help writing a Python script to filter a public star catalog (like Hipparcos) down to the specific magnitude threshold needed for the iPhone?

[1] [https://devblogs.microsoft.com](https://devblogs.microsoft.com/ifdef-windows/astrophotography-with-windows-tiny-pcs-and-wpf/)
[2] [https://www.mdpi.com](https://www.mdpi.com/2072-4292/15/7/1921)
[3] [https://www.youtube.com](https://www.youtube.com/watch?v=oMZdYPJHE8s)
[4] [https://www.mdpi.com](https://www.mdpi.com/2072-4292/14/23/6027)
[5] [https://news.ycombinator.com](https://news.ycombinator.com/item?id=17906113)
[6] [https://arstechnica.com](https://arstechnica.com/science/2022/09/how-an-enormous-project-attempted-to-map-the-sky-without-computers/)
[7] [https://pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC4239958/)
[8] [https://tetra3.readthedocs.io](https://tetra3.readthedocs.io/en/legacy/api_docs.html)
[9] [https://pmc.ncbi.nlm.nih.gov](https://pmc.ncbi.nlm.nih.gov/articles/PMC7070887/)
[10] [https://www.waspacegrant.org](https://www.waspacegrant.org/wordpress/wp-content/uploads/2022/08/SURP2022-Haining_Yang_Zhang.pdf)
[11] [https://astronomy.stackexchange.com](https://astronomy.stackexchange.com/questions/33575/how-the-heck-does-astrometry-net-work)


What is tetra3?

tetra3 is a Python library that identifies stars in astronomical images and determines the celestial direction (right ascension and declination) that a camera is pointing towards. It solves the "lost-in-space" problem: given only an image of stars with no prior knowledge of the camera's orientation, determine where in the sky the camera is pointing.

The system uses a pattern-matching approach where 4-star patterns from the image are compared against a pre-built database of star patterns to find matches. Once stars are identified, the camera's precise orientation is calculated through coordinate transformations.

The default database (default_database.npz) covers 10-30 degree FOV with stars up to magnitude 7. Custom databases can be generated for specific applications using the generate_database method.

Method	Purpose	Typical Use
solve_from_image()	Solve camera pointing from image	Primary solving interface
solve_from_centroids()	Solve from pre-extracted centroids	When centroids already available
generate_database()	Create custom star pattern database	One-time setup for specific FOV
load_database()	Load database from file	Initialize solver with database
save_database()	Save database to file	Persist generated database

Databases are stored as NumPy compressed archives (.npz files) with three primary arrays:
Array	Shape	Contents
star_table	(N, 6)	RA, Dec, x, y, z (unit vectors), magnitude
pattern_catalog	(M, 4)	Hash table of 4-star pattern indices
props_packed	structured	Metadata (FOV range, pattern params, catalog source)

The default database is located at
tetra3/data/default_database.npz and was built with:

    max_fov=30, min_fov=10 (degrees)
    star_max_magnitude=7
    Source catalog: hip_main (Hipparcos)


