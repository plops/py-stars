"""Curated Deep Sky Object (DSO) catalog and FOV projection.

Includes all 110 Messier objects and major prominent NGC objects with J2000 coordinates,
types, common names, visual magnitudes, and angular dimensions.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeepSkyObject:
    """A Deep Sky Object (nebula, galaxy, cluster)."""

    id: str  # e.g., "M31", "M42", "NGC 7000"
    ngc_id: str  # e.g., "NGC 224", "NGC 1976"
    name: str  # e.g., "Andromeda Galaxy", "Orion Nebula"
    obj_type: str  # e.g., "Galaxy", "Emission Nebula", "Open Cluster", "Planetary Nebula"
    constellation: str  # e.g., "And", "Ori", "UMa"
    ra_deg: float  # Right Ascension in degrees (J2000)
    dec_deg: float  # Declination in degrees (J2000)
    magnitude: float  # Apparent visual magnitude
    major_axis_arcmin: float  # Major angular dimension in arcminutes
    minor_axis_arcmin: float  # Minor angular dimension in arcminutes


@dataclass
class ProjectedDSO:
    """A Deep Sky Object projected onto the image plane."""

    dso: DeepSkyObject
    px: float  # Center-origin X in pixels [-W/2, +W/2]
    py: float  # Center-origin Y in pixels [-H/2, +H/2]
    image_x: float  # Top-left origin X in pixels [0, W]
    image_y: float  # Top-left origin Y in pixels [0, H]
    major_axis_px: float  # Projected major size in pixels
    minor_axis_px: float  # Projected minor size in pixels
    is_visible: bool  # True if inside sensor boundary


# Complete Messier Catalog (M1 to M110)
MESSIER_CATALOG: list[DeepSkyObject] = [
    DeepSkyObject(
        "M1", "NGC 1952", "Crab Nebula", "Supernova Remnant", "Tau", 83.633, 22.014, 8.4, 6.0, 4.0
    ),
    DeepSkyObject(
        "M2", "NGC 7089", "", "Globular Cluster", "Aqr", 323.362, -0.823, 6.5, 16.0, 16.0
    ),
    DeepSkyObject(
        "M3", "NGC 5272", "", "Globular Cluster", "CVn", 205.548, 28.376, 6.2, 18.0, 18.0
    ),
    DeepSkyObject(
        "M4", "NGC 6121", "", "Globular Cluster", "Sco", 245.897, -26.526, 5.9, 36.0, 36.0
    ),
    DeepSkyObject(
        "M5", "NGC 5904", "Rose Cluster", "Globular Cluster", "Ser", 229.638, 2.081, 5.7, 23.0, 23.0
    ),
    DeepSkyObject(
        "M6",
        "NGC 6405",
        "Butterfly Cluster",
        "Open Cluster",
        "Sco",
        265.042,
        -32.217,
        4.2,
        25.0,
        25.0,
    ),
    DeepSkyObject(
        "M7",
        "NGC 6475",
        "Ptolemy's Cluster",
        "Open Cluster",
        "Sco",
        268.463,
        -34.823,
        3.3,
        80.0,
        80.0,
    ),
    DeepSkyObject(
        "M8",
        "NGC 6523",
        "Lagoon Nebula",
        "Emission Nebula",
        "Sgr",
        270.921,
        -24.387,
        6.0,
        90.0,
        40.0,
    ),
    DeepSkyObject(
        "M9", "NGC 6333", "", "Globular Cluster", "Oph", 259.799, -18.516, 7.9, 12.0, 12.0
    ),
    DeepSkyObject(
        "M10", "NGC 6254", "", "Globular Cluster", "Oph", 254.288, -4.100, 6.6, 20.0, 20.0
    ),
    DeepSkyObject(
        "M11",
        "NGC 6705",
        "Wild Duck Cluster",
        "Open Cluster",
        "Sct",
        282.767,
        -6.267,
        5.8,
        14.0,
        14.0,
    ),
    DeepSkyObject(
        "M12", "NGC 6218", "", "Globular Cluster", "Oph", 251.812, -1.948, 6.7, 16.0, 16.0
    ),
    DeepSkyObject(
        "M13",
        "NGC 6205",
        "Great Hercules Cluster",
        "Globular Cluster",
        "Her",
        250.422,
        36.460,
        5.8,
        20.0,
        20.0,
    ),
    DeepSkyObject(
        "M14", "NGC 6402", "", "Globular Cluster", "Oph", 264.401, -3.246, 7.6, 11.0, 11.0
    ),
    DeepSkyObject(
        "M15",
        "NGC 7078",
        "Pegasus Cluster",
        "Globular Cluster",
        "Peg",
        322.493,
        12.167,
        6.2,
        18.0,
        18.0,
    ),
    DeepSkyObject(
        "M16",
        "NGC 6611",
        "Eagle Nebula",
        "Emission Nebula",
        "Ser",
        274.700,
        -13.790,
        6.0,
        35.0,
        28.0,
    ),
    DeepSkyObject(
        "M17",
        "NGC 6618",
        "Omega Nebula / Swan Nebula",
        "Emission Nebula",
        "Sgr",
        275.196,
        -16.172,
        6.0,
        11.0,
        11.0,
    ),
    DeepSkyObject(
        "M18", "NGC 6613", "Black Swan", "Open Cluster", "Sgr", 274.988, -17.135, 7.5, 9.0, 9.0
    ),
    DeepSkyObject(
        "M19", "NGC 6273", "", "Globular Cluster", "Oph", 255.657, -26.268, 6.8, 17.0, 17.0
    ),
    DeepSkyObject(
        "M20",
        "NGC 6514",
        "Trifid Nebula",
        "Emission Nebula",
        "Sgr",
        270.630,
        -23.033,
        6.3,
        28.0,
        28.0,
    ),
    DeepSkyObject(
        "M21", "NGC 6531", "Webb's Cross", "Open Cluster", "Sgr", 271.162, -22.500, 6.5, 13.0, 13.0
    ),
    DeepSkyObject(
        "M22",
        "NGC 6656",
        "Sagittarius Cluster",
        "Globular Cluster",
        "Sgr",
        279.100,
        -23.905,
        5.1,
        32.0,
        32.0,
    ),
    DeepSkyObject("M23", "NGC 6494", "", "Open Cluster", "Sgr", 269.217, -19.018, 5.5, 27.0, 27.0),
    DeepSkyObject(
        "M24",
        "IC 4715",
        "Small Sagittarius Star Cloud",
        "Star Cloud",
        "Sgr",
        274.700,
        -18.550,
        4.6,
        90.0,
        90.0,
    ),
    DeepSkyObject("M25", "IC 4725", "", "Open Cluster", "Sgr", 277.942, -19.117, 4.6, 40.0, 40.0),
    DeepSkyObject("M26", "NGC 6694", "", "Open Cluster", "Sct", 281.304, -9.383, 8.0, 15.0, 15.0),
    DeepSkyObject(
        "M27",
        "NGC 6853",
        "Dumbbell Nebula",
        "Planetary Nebula",
        "Vul",
        299.901,
        22.721,
        7.4,
        8.0,
        5.7,
    ),
    DeepSkyObject(
        "M28", "NGC 6626", "", "Globular Cluster", "Sgr", 276.136, -24.870, 6.8, 11.2, 11.2
    ),
    DeepSkyObject(
        "M29", "NGC 6913", "Cooling Tower", "Open Cluster", "Cyg", 305.975, 38.524, 7.1, 7.0, 7.0
    ),
    DeepSkyObject(
        "M30", "NGC 7099", "", "Globular Cluster", "Cap", 325.092, -23.179, 7.2, 12.0, 12.0
    ),
    DeepSkyObject(
        "M31",
        "NGC 224",
        "Andromeda Galaxy",
        "Spiral Galaxy",
        "And",
        10.685,
        41.269,
        3.4,
        190.0,
        60.0,
    ),
    DeepSkyObject(
        "M32", "NGC 221", "Le Gentil", "Elliptical Galaxy", "And", 10.674, 40.865, 8.1, 8.7, 6.5
    ),
    DeepSkyObject(
        "M33",
        "NGC 598",
        "Triangulum Galaxy",
        "Spiral Galaxy",
        "Tri",
        23.462,
        30.660,
        5.7,
        73.0,
        45.0,
    ),
    DeepSkyObject(
        "M34", "NGC 1039", "Spiral Cluster", "Open Cluster", "Per", 40.525, 42.783, 5.5, 35.0, 35.0
    ),
    DeepSkyObject(
        "M35",
        "NGC 2168",
        "Shoe-Buckle Cluster",
        "Open Cluster",
        "Gem",
        92.221,
        24.333,
        5.3,
        28.0,
        28.0,
    ),
    DeepSkyObject(
        "M36",
        "NGC 1960",
        "Pinwheel Cluster",
        "Open Cluster",
        "Aur",
        84.050,
        34.140,
        6.0,
        12.0,
        12.0,
    ),
    DeepSkyObject(
        "M37",
        "NGC 2099",
        "Auriga Salt-and-Pepper",
        "Open Cluster",
        "Aur",
        88.067,
        32.551,
        5.6,
        24.0,
        24.0,
    ),
    DeepSkyObject(
        "M38",
        "NGC 1912",
        "Starfish Cluster",
        "Open Cluster",
        "Aur",
        82.179,
        35.842,
        6.4,
        21.0,
        21.0,
    ),
    DeepSkyObject("M39", "NGC 7092", "", "Open Cluster", "Cyg", 323.050, 48.433, 4.6, 32.0, 32.0),
    DeepSkyObject(
        "M40",
        "Winnecke 4",
        "Winnecke 4 Double Star",
        "Double Star",
        "UMa",
        185.567,
        58.083,
        8.4,
        0.8,
        0.8,
    ),
    DeepSkyObject(
        "M41",
        "NGC 2287",
        "Little Beehive Cluster",
        "Open Cluster",
        "CMa",
        101.754,
        -20.733,
        4.5,
        38.0,
        38.0,
    ),
    DeepSkyObject(
        "M42", "NGC 1976", "Orion Nebula", "Emission Nebula", "Ori", 83.822, -5.391, 4.0, 85.0, 60.0
    ),
    DeepSkyObject(
        "M43",
        "NGC 1982",
        "De Mairan's Nebula",
        "Emission Nebula",
        "Ori",
        83.887,
        -5.271,
        9.0,
        20.0,
        15.0,
    ),
    DeepSkyObject(
        "M44",
        "NGC 2632",
        "Beehive Cluster / Praesepe",
        "Open Cluster",
        "Cnc",
        130.100,
        19.667,
        3.7,
        95.0,
        95.0,
    ),
    DeepSkyObject(
        "M45",
        "",
        "Pleiades / Seven Sisters",
        "Open Cluster",
        "Tau",
        56.750,
        24.117,
        1.6,
        110.0,
        110.0,
    ),
    DeepSkyObject("M46", "NGC 2437", "", "Open Cluster", "Pup", 115.467, -14.817, 6.1, 27.0, 27.0),
    DeepSkyObject("M47", "NGC 2422", "", "Open Cluster", "Pup", 114.150, -14.483, 4.2, 30.0, 30.0),
    DeepSkyObject("M48", "NGC 2548", "", "Open Cluster", "Hya", 123.429, -5.800, 5.5, 54.0, 54.0),
    DeepSkyObject(
        "M49", "NGC 4472", "", "Elliptical Galaxy", "Vir", 187.445, 8.000, 8.4, 10.2, 8.3
    ),
    DeepSkyObject(
        "M50",
        "NGC 2323",
        "Heart-Shaped Cluster",
        "Open Cluster",
        "Mon",
        105.808,
        -8.333,
        5.9,
        16.0,
        16.0,
    ),
    DeepSkyObject(
        "M51",
        "NGC 5194",
        "Whirlpool Galaxy",
        "Spiral Galaxy",
        "CVn",
        202.469,
        47.195,
        8.4,
        11.2,
        6.9,
    ),
    DeepSkyObject(
        "M52",
        "NGC 7654",
        "Scorpion Cluster",
        "Open Cluster",
        "Cas",
        351.200,
        61.593,
        7.3,
        13.0,
        13.0,
    ),
    DeepSkyObject(
        "M53", "NGC 5024", "", "Globular Cluster", "Com", 198.230, 18.168, 7.6, 13.0, 13.0
    ),
    DeepSkyObject(
        "M54", "NGC 6715", "", "Globular Cluster", "Sgr", 283.764, -30.479, 7.6, 12.0, 12.0
    ),
    DeepSkyObject(
        "M55",
        "NGC 6809",
        "Spectre Cluster",
        "Globular Cluster",
        "Sgr",
        294.999,
        -30.965,
        6.3,
        19.0,
        19.0,
    ),
    DeepSkyObject("M56", "NGC 6779", "", "Globular Cluster", "Lyr", 289.148, 30.184, 8.3, 8.8, 8.8),
    DeepSkyObject(
        "M57", "NGC 6720", "Ring Nebula", "Planetary Nebula", "Lyr", 283.396, 33.029, 8.8, 2.5, 2.0
    ),
    DeepSkyObject("M58", "NGC 4579", "", "Spiral Galaxy", "Vir", 189.431, 11.818, 9.7, 5.9, 4.7),
    DeepSkyObject(
        "M59", "NGC 4621", "", "Elliptical Galaxy", "Vir", 190.509, 11.647, 9.6, 5.4, 3.7
    ),
    DeepSkyObject(
        "M60", "NGC 4649", "", "Elliptical Galaxy", "Vir", 190.917, 11.553, 8.8, 7.4, 6.0
    ),
    DeepSkyObject(
        "M61",
        "NGC 4303",
        "Swelling Spiral Galaxy",
        "Spiral Galaxy",
        "Vir",
        185.479,
        4.474,
        9.7,
        6.5,
        5.8,
    ),
    DeepSkyObject(
        "M62",
        "NGC 6266",
        "Flickering Globular Cluster",
        "Globular Cluster",
        "Oph",
        255.303,
        -30.114,
        6.5,
        15.0,
        15.0,
    ),
    DeepSkyObject(
        "M63",
        "NGC 5055",
        "Sunflower Galaxy",
        "Spiral Galaxy",
        "CVn",
        198.956,
        42.029,
        8.6,
        12.6,
        7.2,
    ),
    DeepSkyObject(
        "M64",
        "NGC 4826",
        "Black Eye Galaxy",
        "Spiral Galaxy",
        "Com",
        194.182,
        21.682,
        8.5,
        10.7,
        5.1,
    ),
    DeepSkyObject(
        "M65",
        "NGC 3623",
        "Leo Triplet Galaxy 1",
        "Spiral Galaxy",
        "Leo",
        169.733,
        13.092,
        9.3,
        8.7,
        2.5,
    ),
    DeepSkyObject(
        "M66",
        "NGC 3627",
        "Leo Triplet Galaxy 2",
        "Spiral Galaxy",
        "Leo",
        170.063,
        12.992,
        8.9,
        9.1,
        4.2,
    ),
    DeepSkyObject(
        "M67",
        "NGC 2682",
        "King Cobra Cluster",
        "Open Cluster",
        "Cnc",
        132.825,
        11.817,
        6.1,
        30.0,
        30.0,
    ),
    DeepSkyObject(
        "M68", "NGC 4590", "", "Globular Cluster", "Hya", 189.867, -26.744, 7.8, 11.0, 11.0
    ),
    DeepSkyObject(
        "M69", "NGC 6637", "", "Globular Cluster", "Sgr", 277.846, -32.348, 7.6, 9.8, 9.8
    ),
    DeepSkyObject(
        "M70", "NGC 6681", "", "Globular Cluster", "Sgr", 280.803, -32.292, 7.9, 8.0, 8.0
    ),
    DeepSkyObject("M71", "NGC 6838", "", "Globular Cluster", "Sge", 298.444, 18.779, 8.2, 7.2, 7.2),
    DeepSkyObject(
        "M72", "NGC 6981", "", "Globular Cluster", "Aqr", 313.366, -12.537, 9.3, 6.6, 6.6
    ),
    DeepSkyObject("M73", "NGC 6994", "", "Asterism", "Aqr", 314.725, -12.633, 9.0, 2.8, 2.8),
    DeepSkyObject(
        "M74", "NGC 628", "Phantom Galaxy", "Spiral Galaxy", "Psc", 24.174, 15.783, 9.4, 10.5, 9.5
    ),
    DeepSkyObject(
        "M75", "NGC 6864", "", "Globular Cluster", "Sgr", 301.520, -21.922, 8.5, 6.8, 6.8
    ),
    DeepSkyObject(
        "M76",
        "NGC 650",
        "Little Dumbbell Nebula",
        "Planetary Nebula",
        "Per",
        25.592,
        51.575,
        10.1,
        2.7,
        1.8,
    ),
    DeepSkyObject(
        "M77", "NGC 1068", "Cetus A", "Spiral Galaxy", "Cet", 40.670, -0.013, 8.9, 7.1, 6.0
    ),
    DeepSkyObject("M78", "NGC 2068", "", "Reflection Nebula", "Ori", 86.683, 0.078, 8.3, 8.0, 6.0),
    DeepSkyObject("M79", "NGC 1904", "", "Globular Cluster", "Lep", 81.046, -24.524, 7.7, 9.6, 9.6),
    DeepSkyObject(
        "M80", "NGC 6093", "", "Globular Cluster", "Sco", 244.260, -22.976, 7.3, 10.0, 10.0
    ),
    DeepSkyObject(
        "M81", "NGC 3031", "Bode's Galaxy", "Spiral Galaxy", "UMa", 148.888, 69.065, 6.9, 26.9, 14.1
    ),
    DeepSkyObject(
        "M82",
        "NGC 3034",
        "Cigar Galaxy",
        "Starburst Galaxy",
        "UMa",
        148.968,
        69.680,
        8.4,
        11.2,
        4.3,
    ),
    DeepSkyObject(
        "M83",
        "NGC 5236",
        "Southern Pinwheel Galaxy",
        "Spiral Galaxy",
        "Hya",
        204.254,
        -29.866,
        7.5,
        12.9,
        11.5,
    ),
    DeepSkyObject(
        "M84", "NGC 4374", "", "Lenticular Galaxy", "Vir", 186.266, 12.887, 9.1, 6.5, 5.6
    ),
    DeepSkyObject(
        "M85", "NGC 4382", "", "Lenticular Galaxy", "Com", 186.350, 18.191, 9.1, 7.1, 5.5
    ),
    DeepSkyObject(
        "M86", "NGC 4406", "", "Lenticular Galaxy", "Vir", 186.549, 12.946, 8.9, 8.9, 5.8
    ),
    DeepSkyObject(
        "M87", "NGC 4486", "Virgo A", "Elliptical Galaxy", "Vir", 187.706, 12.391, 8.6, 8.3, 6.6
    ),
    DeepSkyObject("M88", "NGC 4501", "", "Spiral Galaxy", "Com", 187.997, 14.420, 9.6, 6.8, 3.7),
    DeepSkyObject(
        "M89", "NGC 4552", "", "Elliptical Galaxy", "Vir", 188.916, 12.556, 9.8, 5.1, 5.1
    ),
    DeepSkyObject("M90", "NGC 4569", "", "Spiral Galaxy", "Vir", 189.208, 13.163, 9.5, 9.5, 4.4),
    DeepSkyObject("M91", "NGC 4548", "", "Spiral Galaxy", "Com", 188.860, 14.496, 10.2, 5.4, 4.3),
    DeepSkyObject(
        "M92", "NGC 6341", "", "Globular Cluster", "Her", 259.280, 43.136, 6.4, 14.0, 14.0
    ),
    DeepSkyObject(
        "M93",
        "NGC 2447",
        "Butterfly Cluster",
        "Open Cluster",
        "Pup",
        116.142,
        -23.854,
        6.0,
        22.0,
        22.0,
    ),
    DeepSkyObject(
        "M94",
        "NGC 4736",
        "Croc's Eye Galaxy",
        "Spiral Galaxy",
        "CVn",
        192.721,
        41.120,
        8.2,
        11.2,
        9.1,
    ),
    DeepSkyObject("M95", "NGC 3351", "", "Spiral Galaxy", "Leo", 160.991, 11.704, 9.7, 7.3, 4.4),
    DeepSkyObject("M96", "NGC 3368", "", "Spiral Galaxy", "Leo", 161.691, 11.820, 9.2, 7.6, 5.2),
    DeepSkyObject(
        "M97", "NGC 3587", "Owl Nebula", "Planetary Nebula", "UMa", 168.698, 55.019, 9.9, 3.4, 3.3
    ),
    DeepSkyObject("M98", "NGC 4192", "", "Spiral Galaxy", "Com", 183.451, 14.901, 10.1, 9.8, 2.8),
    DeepSkyObject(
        "M99", "NGC 4254", "Coma Pinwheel", "Spiral Galaxy", "Com", 184.707, 14.416, 9.9, 5.4, 4.7
    ),
    DeepSkyObject(
        "M100",
        "NGC 4321",
        "Mirror Pattern Galaxy",
        "Spiral Galaxy",
        "Com",
        185.729,
        15.822,
        9.3,
        7.4,
        6.3,
    ),
    DeepSkyObject(
        "M101",
        "NGC 5457",
        "Pinwheel Galaxy",
        "Spiral Galaxy",
        "UMa",
        210.802,
        54.349,
        7.9,
        28.8,
        26.9,
    ),
    DeepSkyObject(
        "M102",
        "NGC 5866",
        "Spindle Galaxy",
        "Lenticular Galaxy",
        "Dra",
        226.623,
        55.763,
        9.9,
        4.7,
        1.9,
    ),
    DeepSkyObject("M103", "NGC 581", "", "Open Cluster", "Cas", 23.338, 60.700, 7.4, 6.0, 6.0),
    DeepSkyObject(
        "M104",
        "NGC 4594",
        "Sombrero Galaxy",
        "Spiral Galaxy",
        "Vir",
        189.998,
        -11.623,
        8.0,
        8.7,
        3.5,
    ),
    DeepSkyObject(
        "M105", "NGC 3379", "", "Elliptical Galaxy", "Leo", 161.957, 12.582, 9.3, 5.4, 4.8
    ),
    DeepSkyObject("M106", "NGC 4258", "", "Spiral Galaxy", "CVn", 184.740, 47.304, 8.4, 18.6, 7.2),
    DeepSkyObject(
        "M107", "NGC 6171", "", "Globular Cluster", "Oph", 248.133, -13.054, 7.9, 13.0, 13.0
    ),
    DeepSkyObject(
        "M108",
        "NGC 3556",
        "Surfboard Galaxy",
        "Spiral Galaxy",
        "UMa",
        167.879,
        55.674,
        10.0,
        8.7,
        2.2,
    ),
    DeepSkyObject(
        "M109",
        "NGC 3992",
        "Vacuum Cleaner Galaxy",
        "Spiral Galaxy",
        "UMa",
        179.399,
        53.375,
        9.8,
        7.6,
        4.7,
    ),
    DeepSkyObject(
        "M110",
        "NGC 205",
        "Edward Young Star",
        "Dwarf Elliptical Galaxy",
        "And",
        10.092,
        41.685,
        8.1,
        21.9,
        11.0,
    ),
]

# Prominent Bright Non-Messier NGC / Caldwell Objects
BRIGHT_NGC_CATALOG: list[DeepSkyObject] = [
    DeepSkyObject(
        "NGC 7000",
        "C 20",
        "North America Nebula",
        "Emission Nebula",
        "Cyg",
        314.750,
        44.333,
        4.0,
        120.0,
        100.0,
    ),
    DeepSkyObject(
        "NGC 869",
        "h Persei",
        "Double Cluster (h Persei)",
        "Open Cluster",
        "Per",
        34.750,
        57.133,
        3.7,
        30.0,
        30.0,
    ),
    DeepSkyObject(
        "NGC 884",
        "χ Persei",
        "Double Cluster (chi Persei)",
        "Open Cluster",
        "Per",
        35.550,
        57.150,
        3.8,
        30.0,
        30.0,
    ),
    DeepSkyObject(
        "NGC 2237",
        "C 49",
        "Rosette Nebula",
        "Emission Nebula",
        "Mon",
        97.975,
        5.010,
        9.0,
        80.0,
        60.0,
    ),
    DeepSkyObject(
        "NGC 6960",
        "C 34",
        "Western Veil Nebula (Witch's Broom)",
        "Supernova Remnant",
        "Cyg",
        311.400,
        30.717,
        7.0,
        70.0,
        6.0,
    ),
    DeepSkyObject(
        "NGC 6992",
        "C 33",
        "Eastern Veil Nebula",
        "Supernova Remnant",
        "Cyg",
        313.900,
        31.717,
        7.0,
        60.0,
        8.0,
    ),
    DeepSkyObject(
        "NGC 253",
        "C 65",
        "Sculptor Galaxy / Silver Coin",
        "Spiral Galaxy",
        "Scl",
        11.888,
        -25.288,
        7.2,
        27.5,
        6.8,
    ),
    DeepSkyObject(
        "NGC 7293",
        "C 63",
        "Helix Nebula",
        "Planetary Nebula",
        "Aqr",
        337.410,
        -20.837,
        7.6,
        25.0,
        16.0,
    ),
    DeepSkyObject(
        "NGC 1499",
        "C 12",
        "California Nebula",
        "Emission Nebula",
        "Per",
        60.800,
        36.617,
        6.0,
        160.0,
        40.0,
    ),
    DeepSkyObject(
        "NGC 4565", "C 38", "Needle Galaxy", "Spiral Galaxy", "Com", 189.087, 25.988, 9.6, 15.9, 1.9
    ),
    DeepSkyObject(
        "NGC 891",
        "C 23",
        "Silver Sliver Galaxy",
        "Spiral Galaxy",
        "And",
        35.639,
        42.349,
        9.9,
        13.5,
        2.5,
    ),
    DeepSkyObject(
        "IC 434",
        "",
        "Horsehead Nebula (region)",
        "Emission/Dark Nebula",
        "Ori",
        85.246,
        -2.460,
        7.3,
        60.0,
        10.0,
    ),
]

FULL_DSO_CATALOG: list[DeepSkyObject] = MESSIER_CATALOG + BRIGHT_NGC_CATALOG


def get_all_dsos() -> list[DeepSkyObject]:
    """Return the complete deep sky object catalog."""
    return list(FULL_DSO_CATALOG)


def find_dso_by_name(query: str) -> list[DeepSkyObject]:
    """Search DSOs by catalog ID (e.g. 'M31', 'NGC 7000') or name (e.g. 'Andromeda')."""
    q = query.strip().lower()
    matches = []
    for dso in FULL_DSO_CATALOG:
        if (
            q == dso.id.lower()
            or q in dso.name.lower()
            or q in dso.ngc_id.lower()
            or q == dso.constellation.lower()
        ):
            matches.append(dso)
    return matches


def project_dsos_to_image(
    solve_result: Any,
    image_width: int,
    image_height: int,
    max_magnitude: float | None = None,
    object_types: list[str] | None = None,
    catalog: list[DeepSkyObject] | None = None,
) -> list[ProjectedDSO]:
    """Project deep sky objects in the catalog onto the plate-solved image plane.

    Args:
        solve_result: Successful tetra3rs.SolveResult with world_to_pixel method and fov_deg.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        max_magnitude: Optional magnitude limit (fainter objects excluded).
        object_types: Optional list of object types to include (e.g. ['Galaxy', 'Emission Nebula']).
        catalog: Optional custom DSO catalog (defaults to FULL_DSO_CATALOG).

    Returns:
        List of ProjectedDSO instances located inside the image frame.
    """
    if catalog is None:
        catalog = FULL_DSO_CATALOG

    w = float(image_width)
    h = float(image_height)
    half_w = w / 2.0
    half_h = h / 2.0

    # Scale: arcmin per pixel
    arcsec_per_pixel = (solve_result.fov_deg * 3600.0) / w
    arcmin_per_pixel = arcsec_per_pixel / 60.0

    projected_list: list[ProjectedDSO] = []

    for dso in catalog:
        if max_magnitude is not None and dso.magnitude > max_magnitude:
            continue
        if object_types is not None and dso.obj_type not in object_types:
            continue

        # Project RA/Dec to camera sensor
        try:
            px, py = solve_result.world_to_pixel(dso.ra_deg, dso.dec_deg)
        except Exception:
            continue

        # Check bounds
        is_visible = -half_w <= px <= half_w and -half_h <= py <= half_h
        if is_visible:
            # Convert center-origin to top-left image coordinates
            img_x = px + half_w
            img_y = py + half_h

            major_px = (
                max(4.0, dso.major_axis_arcmin / arcmin_per_pixel) if arcmin_per_pixel > 0 else 10.0
            )
            minor_px = (
                max(4.0, dso.minor_axis_arcmin / arcmin_per_pixel) if arcmin_per_pixel > 0 else 10.0
            )

            projected_list.append(
                ProjectedDSO(
                    dso=dso,
                    px=px,
                    py=py,
                    image_x=img_x,
                    image_y=img_y,
                    major_axis_px=major_px,
                    minor_axis_px=minor_px,
                    is_visible=True,
                )
            )

    return projected_list
