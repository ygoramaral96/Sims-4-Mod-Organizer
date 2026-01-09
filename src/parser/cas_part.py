import struct
import logging
import os
from typing import Optional
from .dbpf import DBPFFile
from .simdata import SIMDATAParser, SIMDATA_TYPE_ID

logger = logging.getLogger(__name__)

# CAS Part Resource Type ID
CAS_PART_TYPE_ID = 0x034AEECB

# Additional resource Type IDs for fallback detection
GEOM_TYPE_ID = 0x015A1849  # 3DMesh/Geometry - all CAS items have this
MLOD_TYPE_ID = 0x01D10F34  # Model LOD

# BodyType Enum Mapping
# Based on Sims 4 community documentation and tuning files
BODY_TYPE_MAP = {
    0: "None",
    1: "Hair",
    2: "Head Accessory",  # Hats
    3: "Face Accessory",  # Glasses
    4: "Top",
    5: "Bottom",
    6: "Full Body",
    7: "Shoes",
    8: "Accessories", # General/Hands/Gloves?
    9: "Accessories", # Socks?
    10: "Make Up",
    11: "Make Up",
    12: "Make Up",
    13: "Make Up",
    14: "Skin Detail",
    15: "Body Hair",
    # Specific specialized slots often map to general categories for organizing
    # Mapping more specific internals to user-friendly folders
}

# Extended mapping for better categorization
CATEGORY_MAP = {
    1: "Hair",
    2: "Accessories/Hats",
    3: "Accessories/Glasses",
    4: "Clothing/Tops",
    5: "Clothing/Bottoms",
    6: "Clothing/FullBody",
    7: "Shoes",
    8: "Accessories/Gloves",
    9: "Accessories/Socks",
    10: "MakeUp/Necklace", # Slot 10 is actually Necklace often? No, let's verify.
    # Actually, let's use a simpler safe categorization first.
    # 57: SkinDetail
}

# Refined list based on common findings
# 1: Hair
# 2: Hat
# 3: Head (General)
# 4: Body (Upper) -> Top
# 5: Body (Lower) -> Bottom
# 6: Body (Full) -> FullBody
# 7: Feet -> Shoes
# 8: Hands -> Gloves
# 9: Wrists -> Bracelets
# 10: Index Finger
# 11: Ring Finger
# 12: Middle Finger
# 13: Ankle
# 14: Necklace
# 15: Earrings
# ...
# 55: Facial Hair
# 56: Lips (Lipstick)
# 57: Eyes (Shadow)
# 58: Eyeliner
# 59: Blush
# 60: Facepaint
# 61: Eyebrows

class CASPart:
    def __init__(self, data: bytes):
        self.data = data
        self.body_type = self._parse_body_type()

    def _parse_body_type(self) -> int:
        """
        Parse BodyType from CASP resource with version-aware offset detection.
        
        Based on Sims 4 community research and s4pi:
        - Version 32+ (0x20): BodyType at offset 20
        - Version 28-31 (0x1C-0x1F): BodyType at offset 16
        - Older versions: BodyType at offset 12
        """
        if len(self.data) < 24:
            return 0
        
        try:
            version = struct.unpack('<I', self.data[0:4])[0]
            
            # Version-specific offsets based on s4pi CASP structure documentation
            if version >= 0x20:  # Version 32 and above (modern Sims 4)
                # Most common in current game
                if len(self.data) >= 24:
                    return struct.unpack('<I', self.data[20:24])[0]
            elif version >= 0x1C:  # Version 28-31
                if len(self.data) >= 20:
                    return struct.unpack('<I', self.data[16:20])[0]
            else:  # Older versions
                if len(self.data) >= 16:
                    return struct.unpack('<I', self.data[12:16])[0]
        except (struct.error, IndexError):
            pass
        
        # Fallback: try multiple offsets in order of likelihood
        for offset in [20, 16, 12, 24, 28]:
            try:
                if len(self.data) >= offset + 4:
                    body_type = struct.unpack('<I', self.data[offset:offset+4])[0]
                    # Body type should be in reasonable range (0-100)
                    if 0 <= body_type <= 100:
                        return body_type
            except (struct.error, IndexError):
                continue
        
        return 0

    def get_category(self) -> str:
        """
        Map BodyType value to user-friendly category folder.
        
        Based on Sims 4 BodyType enum values from community research.
        """
        bt = self.body_type
        
        # Core clothing categories
        if bt == 1: return "Hair"
        if bt == 2: return "Accessories/Hats"
        if bt == 3: return "Accessories/Head"
        if bt == 4: return "Clothing/Tops"
        if bt == 5: return "Clothing/Bottoms"
        if bt == 6: return "Clothing/FullBody"
        if bt == 7: return "Shoes"
        
        # Accessory categories
        if bt in [8, 9]: return "Accessories/Hands"  # Gloves, Wrists
        if bt in [10, 11, 12]: return "Accessories/Rings"  # Finger rings
        if bt == 13: return "Accessories/Anklets"
        if bt == 14: return "Accessories/Necklaces"
        if bt == 15: return "Accessories/Earrings"
        
        # Makeup and facial features
        if bt == 55: return "FacialHair"
        if bt in [56, 57, 58, 59, 60, 61]: return "Makeup"  # Lips, eyes, blush, etc.
        
        # Skin details
        if bt in [62, 63, 64]: return "SkinDetails"  # Tattoos, scars, etc.
        
        return "Uncategorized"


def _try_simdata_detection(dbpf: DBPFFile) -> Optional[str]:
    """
    Attempt to detect category from SIMDATA resources.
    SIMDATA files may contain tag arrays that indicate CAS categories.
    """
    simdata_entries = [entry for entry in dbpf.index_entries if entry.type_id == SIMDATA_TYPE_ID]
    
    if not simdata_entries:
        logger.debug("No SIMDATA resources found in package")
        return None
   
    logger.debug(f"Found {len(simdata_entries)} SIMDATA resources, attempting tag extraction...")
    
    for entry in simdata_entries[:3]:  # Only check first few to avoid performance issues
        try:
            content = dbpf.get_resource_content(entry)
            if not content or len(content) < 16:
                continue
            
            parser = SIMDATAParser(content)
            tags = parser.parse_tags()
            
            if tags:
                logger.debug(f"Extracted {len(tags)} tags from SIMDATA: {[hex(t) for t in tags[:5]]}")
                # Attempt to guess category from tags
                category = parser.guess_category_from_tags(tags)
                if category:
                    return category
        except Exception as e:
            logger.debug(f"Error parsing SIMDATA resource: {e}")
            continue
    
    return None


def get_package_category(dbpf: DBPFFile) -> str:
    """
    Determine mod category by analyzing package contents.
    
    Primary method: Look for CAS Part resources and extract BodyType.
    Fallback1: Use filename heuristics if CASP not found
    Fallback2: Check for GEOM resources (all CAS items have meshes)
    """
    # Debug: Log total entries and unique types
    unique_types = set(entry.type_id for entry in dbpf.index_entries)
    logger.debug(f"Package has {len(dbpf.index_entries)} entries with {len(unique_types)} unique types")
    logger.debug(f"Type IDs present: {[hex(t) for t in sorted(unique_types)][:10]}...")  # Show first 10
    
    cas_parts_found = 0
    # Primary: Scan index for CAS Parts
    for entry in dbpf.index_entries:
        if entry.type_id == CAS_PART_TYPE_ID:
            cas_parts_found += 1
            try:
                logger.debug(f"Found CAS Part #{cas_parts_found}, decompressing...")
                data = dbpf.get_resource_content(entry)
                logger.debug(f"CAS Part data size: {len(data)} bytes")
                
                cas_part = CASPart(data)
                logger.debug(f"Parsed BodyType: {cas_part.body_type}")
                
                cat = cas_part.get_category()
                logger.debug(f"Category result: {cat}")
                
                if cat != "Uncategorized":
                    logger.info(f"Successfully categorized via BodyType {cas_part.body_type} -> {cat}")
                    return cat
            except Exception as e:
                logger.warning(f"Failed to parse CAS Part: {e}")
                continue
    
    # Fallback 1: Try SIMDATA tag extraction for merged packages
    if cas_parts_found == 0:
        logger.debug("No CASP resources, attempting SIMDATA tag extraction...")
        simdata_category = _try_simdata_detection(dbpf)
        if simdata_category:
            logger.info(f"✓ Category from SIMDATA: {simdata_category}")
            return simdata_category
    
    # Fallback 2: Use filename heuristics for CC without CASP resources
    if cas_parts_found == 0:
        logger.info("SIMDATA unsuccessful, using filename heuristics...")
        
        # Skip macOS resource fork files
        filename = os.path.basename(dbpf.file_path)
        if filename.startswith('._'):
            logger.info(f"Skipping macOS resource fork file: {filename}")
            return "Uncategorized"
        
        filename_lower = dbpf.file_path.lower()
        
        # Hair detection
        if any(keyword in filename_lower for keyword in ['hair', 'hairstyle', 'ponytail', 'braid', 'bangs', 'bun', 'hairline']):
            logger.info(f"Detected as Hair via filename")
            return "Hair"
        
        # Hats (Headwear)
        if any(keyword in filename_lower for keyword in ['hat', 'cap', 'beanie', 'helmet', 'crown', 'tiara', 'headband']):
            logger.info(f"Detected as Hats via filename")
            return "Hats"
        
        # Glasses
        if any(keyword in filename_lower for keyword in ['glass', 'sunglass', 'eyewear', 'spectacle', 'monocle']):
            logger.info(f"Detected as Glasses via filename")
            return "Glasses"
        
        # Earrings
        if any(keyword in filename_lower for keyword in ['earring', 'piercing']):
            logger.info(f"Detected as Earrings via filename")
            return "Earrings"
        
        # Necklaces
        if any(keyword in filename_lower for keyword in ['necklace', 'choker', 'collar']):
            logger.info(f"Detected as Necklaces via filename")
            return "Necklaces"
        
        # Full Body Outfits (check before tops/bottoms since they contain those keywords)
        if any(keyword in filename_lower for keyword in ['dress', 'gown', 'bodysuit', 'jumpsuit', 'romper', 'overall', 'outfit']):
            logger.info(f"Detected as Full Body Outfits via filename")
            return "Full Body Outfits"
        
        # Swimwear patterns
        if any(keyword in filename_lower for keyword in ['swimsuit', 'bikini', 'monokini', 'swim', 'bathing']):
            logger.info(f"Detected as Full Body Outfits (swimwear) via filename")
            return "Full Body Outfits"
        
        # Tops (Upper Body)
        if any(keyword in filename_lower for keyword in ['top', 'shirt', 'blouse', 'sweater', 'jacket', 'coat', 'blazer', 'tee', 'crop', 'bra', 'corset', 'turtleneck']):
            logger.info(f"Detected as Tops via filename")
            return "Tops"
        
        # Bottoms (Lower Body)
        if any(keyword in filename_lower for keyword in ['bottom', 'pants', 'jeans', 'trousers', 'shorts', 'leggings', 'skirt', 'slacks', 'joggers', 'breeches', 'tutu']):
            logger.info(f"Detected as Bottoms via filename")
            return "Bottoms"
        
        # Shoes
        if any(keyword in filename_lower for keyword in ['shoe', 'boot', 'sneaker', 'heel', 'sandal', 'slipper', 'feet']):
            logger.info(f"Detected as Shoes via filename")
            return "Shoes"
        
        # Accessories (general - gloves, bracelets, bags, etc.)
        if any(keyword in filename_lower for keyword in [
            'bracelet', 'glove', 'ring', 'bag', 'purse', 'backpack',
            'accessory', 'accessorie', 'wristband', 'gaiter',
            'belt', 'scarf', 'tie'
        ]):
            logger.info(f"Detected as Accessories via filename")
            return "Accessories"
        
        # Socks/Tights
        if any(keyword in filename_lower for keyword in ['sock', 'tight', 'thights', 'stocking', 'legwear', 'pantyhose', 'panties']):
            logger.info(f"Detected as Accessories (legwear) via filename")
            return "Accessories"
        
        # Masks and face accessories
        if any(keyword in filename_lower for keyword in ['mask', 'eyepatch', 'veil', 'headphones', 'controller', 'wings', 'bandage', 'bandages']):
            logger.info(f"Detected as Accessories (face/head) via filename")
            return "Accessories"
        
        # Makeup
        if any(keyword in filename_lower for keyword in ['makeup', 'eyeshadow', 'eyeliner', 'lipstick', 'blush', 'eyebrow', 'nails', 'gloss']):
            logger.info(f"Detected as Makeup via filename")
            return "Makeup"
        
        # Check if has GEOM resources (mesh-based items are CAS)
        has_geom = any(entry.type_id == GEOM_TYPE_ID for entry in dbpf.index_entries)
        
        if has_geom:
            # Has mesh but no keyword match - it's a CAS item we can't categorize
            logger.info("Has GEOM but couldn't determine category - using Other")
            return "Other"
        else:
            # No GEOM, no CASP, no keywords = not a CAS item (script, tuning, etc.)
            logger.info("No CAS indicators - skipping (non-CAS mod)")
            return None
    
    # No CAS Parts found or all failed to parse
    if cas_parts_found == 0:
        logger.info(f"No CAS Parts found (Type ID {hex(CAS_PART_TYPE_ID)}), categorizing as Other")
    else:
        logger.info(f"Found {cas_parts_found} CAS Parts but all were Uncategorized")
    
    return "Other"
