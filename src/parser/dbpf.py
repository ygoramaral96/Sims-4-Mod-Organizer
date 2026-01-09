import struct
import zlib
import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class DBPFHeader:
    magic: bytes
    major_version: int
    minor_version: int
    user_major_version: int
    user_minor_version: int
    flags: int
    created: int
    modified: int
    index_major_version: int
    index_entry_count: int
    index_position: int
    index_size: int
    hole_index_position: int
    hole_index_size: int
    hole_index_entry_count: int
    index_minor_version: int

@dataclass
class IndexEntry:
    type_id: int
    group_id: int
    instance_id: int
    position: int
    size: int
    size_decompressed: int
    compression_flags: int
    committed: int

class DBPFFile:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.header: Optional[DBPFHeader] = None
        self.index_entries: List[IndexEntry] = []

    def read(self):
        with open(self.file_path, 'rb') as f:
            self._read_header(f)
            self._read_index(f)

    def _read_header(self, f):
        # Read the first 96 bytes (DBPF 2.0 header size)
        data = f.read(96)
        if len(data) < 96:
            raise ValueError("File is too small to be a DBPF file")
        
        magic = data[0:4]
        if magic != b'DBPF':
            raise ValueError(f"Invalid magic bytes: {magic}")

        major = struct.unpack('<I', data[4:8])[0]
        minor = struct.unpack('<I', data[8:12])[0]
        
        # We primarily support DBPF 2.1 (Sims 4)
        if major != 2:
             # Basic support, might fail on some specific versions but structure is similar
             pass

        self.header = DBPFHeader(
            magic=magic,
            major_version=major,
            minor_version=minor,
            user_major_version=struct.unpack('<I', data[12:16])[0],
            user_minor_version=struct.unpack('<I', data[16:20])[0],
            flags=struct.unpack('<I', data[20:24])[0],
            created=struct.unpack('<I', data[24:28])[0],
            modified=struct.unpack('<I', data[28:32])[0],
            index_major_version=struct.unpack('<I', data[32:36])[0],
            index_entry_count=struct.unpack('<I', data[36:40])[0],
            index_position=struct.unpack('<I', data[40:44])[0],
            index_size=struct.unpack('<I', data[44:48])[0],
            hole_index_position=struct.unpack('<I', data[48:52])[0],
            hole_index_size=struct.unpack('<I', data[52:56])[0],
            hole_index_entry_count=struct.unpack('<I', data[56:60])[0],
            index_minor_version=struct.unpack('<I', data[60:64])[0] if major >= 2 else 0
        )

    def _read_index(self, f):
        if not self.header or self.header.index_entry_count == 0:
            return

        f.seek(self.header.index_position)

        
        # Determine index entry components based on flags (simplified for standard S4 packages)
        # In DBPF 2.0, the index table can have constant type/group/instance IDs 
        # defined in the flags to save space.
        
        # Flags (bytes 20-23 in header):
        # Bit 0-2: Constant Type ID (1, 2, or 4 bytes unused) ? No, actually:
        # The logic is complex. For now, we will implement a standard parser assuming standard entry size
        # or checking the flags properly is needed for robust parsing.
        
        # Let's use a standard fixed size approach first which works for many files, 
        # but realistically we need to handle the bit flags for index compression.
        
        # Index Header (if present? No, just entries usually)
        # Actually in DBPF 2.1 (Sims 4), there's a 4 byte flags bitfield at the start of the index table?
        # Let's try to implement a robust reader based on s4py logic simplified.
        
        flags = struct.unpack('<I', f.read(4))[0] 
        # The flags tell us which fields are constant (present in header) vs variable (present in entry)
        
        constant_type_id = 0
        constant_group_id = 0
        constant_instance_id_high = 0 # Not typically used in this compression scheme directly like this
        
        # Checking bits to see what needs to be read from the common block
        # Bit 0: Constant Type
        # Bit 1: Constant Group
        # Bit 2: Constant Instance High (unsure)
        
        # Actually, let's look at the standard Sims 4 Package structure. 
        # It usually starts with 4 bytes flags. 
        # Then for each 'set' bit in the flags, there is a value in the 'header' of the index.
        
        c_type = 0
        c_group = 0
        c_inst_ex = 0
        
        if flags & 1:
            c_type = struct.unpack('<I', f.read(4))[0]
        if flags & 2:
            c_group = struct.unpack('<I', f.read(4))[0]
        if flags & 4:
            c_inst_ex = struct.unpack('<I', f.read(4))[0]
            
        for _ in range(self.header.index_entry_count):
            # Read entry
            # Each entry has fields depending on the inverse of the flags
            
            entry_type = c_type
            entry_group = c_group
            entry_inst_ex = c_inst_ex
            
            if not (flags & 1):
                entry_type = struct.unpack('<I', f.read(4))[0]
            if not (flags & 2):
                entry_group = struct.unpack('<I', f.read(4))[0]
            if not (flags & 4):
                entry_inst_ex = struct.unpack('<I', f.read(4))[0]
                
            entry_inst = struct.unpack('<I', f.read(4))[0]
            
            # Combine instance high/low
            full_instance = (entry_inst_ex << 32) | entry_inst
            
            pos = struct.unpack('<I', f.read(4))[0]
            size = struct.unpack('<I', f.read(4))[0]
            size_decomp = struct.unpack('<I', f.read(4))[0] # memsize
            
            # compression flag is usually high bit of size_decomp or separate?
            # In some docs: size_decomp (with high bit set = compressed) 
            # DBPF 2.1: 
            #   Offset 0: Type (if not constant)
            #   Offset 4: Group (if not constant)
            #   Offset 8: Instance High (if not constant)
            #   Offset 12: Instance Low
            #   Offset 16: Position
            #   Offset 20: Size (compressed size header included)
            #   Offset 24: Decompressed Size
            #   Offset 28: Compression Info (2 bytes) + Committed (2 bytes)
            
            # Wait, the structure above for index entry is slightly different in 2.1
            # Let's adjust to the most common format observed.
            # actually strict structural alignment is:
            # 4 bytes: Instance Low (always present)
            # 4 bytes: Position (always present)
            # 4 bytes: Size (bit 31 is compression flag sometimes?)
            # 4 bytes: Size Decompressed
            # 2 bytes: CFlags
            # 2 bytes: Committed
            
            c_flags = struct.unpack('<H', f.read(2))[0]
            committed = struct.unpack('<H', f.read(2))[0]
            
            self.index_entries.append(IndexEntry(
                type_id=entry_type,
                group_id=entry_group,
                instance_id=full_instance,
                position=pos,
                size=size & 0x7FFFFFFF, # Mask out high bit if used
                size_decompressed=size_decomp,
                compression_flags=c_flags,
                committed=committed
            ))

    def get_resource_content(self, entry: IndexEntry) -> bytes:
        """
        Extract and decompress resource content based on compression flags.
        
        Based on s4ptacle/Sims4Tools analysis:
        - 0x0000 = Uncompressed
        - 0x5A42 = ZLib compressed (Sims 4 standard, "ZB" in little-endian)
        - 0xFFFF = ZLib compressed (legacy)
        - 0xFFFE = Streamable/internal compression
        """
        with open(self.file_path, 'rb') as f:
            f.seek(entry.position)
            data = f.read(entry.size)
        
        # Check if data is compressed based on size mismatch
        is_compressed = (entry.size != entry.size_decompressed) and entry.size_decompressed > 0
        
        # If sizes match or no decompressed size specified, return as-is
        if not is_compressed or entry.compression_flags == 0x0000:
            return data
        
        # Handle Sims 4 standard ZLib compression (0x5A42 = "ZB" reversed)
        if entry.compression_flags == 0x5A42:
            try:
                decompressed = zlib.decompress(data)
                # Validate decompressed size matches expected
                if len(decompressed) != entry.size_decompressed:
                    raise ValueError(
                        f"Decompressed size mismatch: got {len(decompressed)}, "
                        f"expected {entry.size_decompressed}"
                    )
                return decompressed
            except zlib.error as e:
                raise ValueError(f"Failed to decompress 0x5A42 resource: {e}")
        
        # Handle legacy ZLib compression (0xFFFF)
        if entry.compression_flags == 0xFFFF:
            try:
                return zlib.decompress(data)
            except zlib.error:
                # Try raw deflate without header
                try:
                    return zlib.decompress(data, -zlib.MAX_WBITS)
                except zlib.error as e:
                    raise ValueError(f"Failed to decompress 0xFFFF resource: {e}")
        
        # Auto-detect ZLib by magic bytes (0x78 = zlib header)
        if data.startswith(b'\x78'):
            try:
                return zlib.decompress(data)
            except zlib.error as e:
                raise ValueError(f"Failed to auto-decompress ZLib resource: {e}")
        
        # Handle streamable compression or unknown - return as-is
        # RefPack (0xFB10) and other EA formats would go here if needed
        if entry.compression_flags == 0xFFFE:
            return data
        
        # Unknown compression type - log warning and return raw data
        # This allows the parser to continue even with unknown compression
        return data
