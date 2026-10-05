from pathlib import Path
import os

# returns zero if could not parse the file
def get_ogg_opus_duration(path):
    file_size = os.path.getsize(path)
    read_size = min(file_size, 65536)
    
    with open(path, 'rb') as f:
        ogg_header = f.read(28)
        
        if len(ogg_header) != 28:
            return 0
        if ogg_header[:4] != b'OggS':
            return 0
        if ogg_header[4] != 0:
            return 0
        
        opus_head = f.read(19)
        if len(opus_head) != 19:
            return 0
        if opus_head[:8] != b'OpusHead':
            return 0
        
        pre_skip = int.from_bytes(opus_head[10:11], 'little')
        freq = int.from_bytes(opus_head[12:16], 'little')
        
        # searching last OggS page from end
        absolute_offset = 0
        i = 0
        while True:
            f.seek(file_size - read_size * i)
            buffer = f.read(read_size)
            
            match_idx = buffer.rfind(b'OggS')
            
            if match_idx != -1:
                absolute_offset = (file_size - read_size) + match_idx
                break
            i += 1
        if absolute_offset == 0:
            raise ValueError('could not find last OggS page')
        
        # reading OggS page
        f.seek(absolute_offset)
        last_oggs_page = f.read(14)
        
        if len(last_oggs_page) != 14:
            return 0
        
        last_granule_position = int.from_bytes(last_oggs_page[6:13], 'little')
        
        return round((last_granule_position - pre_skip) / freq)
        