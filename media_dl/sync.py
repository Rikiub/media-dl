import re

from rich import print
import m3u8
from m3u8 import protocol
from m3u8.parser import save_segment_custom_value


def custom_tags(line: str, lineno, data, state):
    if line.startswith("#EXT-PLAYLIST"):
        chunks = line.replace(protocol.extinf + ":", "").split(" ")
        additional_props = {}

        if len(chunks) <= 1:
            raise ValueError()
        else:
            ...

        matched_props = re.finditer(r'([\w\-]+)="([^"]*)"', chunks[1])
        for match in matched_props:
            additional_props[match.group(1)] = match.group(2)
        chunks[1].split(" ")

        print(additional_props)

        save_segment_custom_value(state, "ext_props", additional_props)

        state["expect_segment"] = True
    elif line.startswith(protocol.extinf):
        title = ""
        chunks = line.replace(protocol.extinf + ":", "").split(",", 1)

        if len(chunks) == 2:
            duration_and_props, title = chunks
        elif len(chunks) == 1:
            duration_and_props = chunks[0]
        else:
            raise ValueError()

        additional_props = {}
        chunks = duration_and_props.strip().split(" ", 1)

        if len(chunks) == 2:
            duration, raw_props = chunks
            matched_props = re.finditer(r'([\w\-]+)="([^"]*)"', raw_props)
            for match in matched_props:
                additional_props[match.group(1)] = match.group(2)
        else:
            duration = duration_and_props

        if "segment" not in state:
            state["segment"] = {}
        state["segment"]["duration"] = float(duration)
        state["segment"]["title"] = title

        # Helper function for saving custom values
        save_segment_custom_value(state, "ext_props", additional_props)

        # Tell 'main parser' that we expect an URL on next lines
        state["expect_segment"] = True

    # Tell 'main parser' that it can go to next line, we've parsed current fully.
    return True


text = """#EXTM3U8
#EXT-PLAYLIST: title=XD url=https://youtube.com/

#EXTINF:0 id="XD", SUB URBAN - RABBIT HOLE
./xd.mp4

#EXTINF:0 id="214asd234" pero="XD", SUB URBAN - CANDYMAN
./jaja.mp4
"""

playlist = m3u8.loads(text, custom_tags_parser=custom_tags)

for item in playlist.segments:
    result = item.custom_parser_values["ext_props"]
    print(result)
