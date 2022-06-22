from io import BufferedReader
import struct
from typing import Any, Literal, Tuple, Union


def readint(
    stream: BufferedReader,
    size: int,
    endian: Literal["little", "big"] = "little",
    signed: bool = False,
) -> int:
    return int.from_bytes(stream.read(size), byteorder=endian, signed=signed)

def readintoffset(
    stream: BufferedReader,
    offset: int,
    size: int,
    endian: Literal["little", "big"] = "little",
    signed: bool = False,
) -> int:
    return_offset = stream.tell()
    stream.seek(offset)
    output = readint(stream, size, endian, signed)
    stream.seek(return_offset)
    return output


def readfloat(stream: BufferedReader) -> float:
    return struct.unpack("<f", stream.read(4))[0]


def readtext(
    stream: BufferedReader, encoding: str = "utf-8", raw: bool = False
) -> str | bytes:
    output = b""
    char = stream.read(1)
    while char != b"\0":
        output += char
        char = stream.read(1)

    if raw:
        return output
    else:
        return output.decode(encoding)


def readtextoffset(stream: BufferedReader, offset: int, encoding: str = "utf-8") -> str:
    return_offset = stream.tell()
    stream.seek(offset)
    output = readtext(stream, raw=True)
    stream.seek(return_offset)
    return output.decode(encoding)


def process_number(
    stream: BufferedReader, datatype: str, signed: bool = False
) -> Tuple[Union[float, int], int]:
    int_size = {"byte": 1, "short": 2, "int": 4, "long": 8}
    if datatype in int_size:
        return readint(stream, int_size[datatype], signed=signed), int_size[datatype]
    else:
        return readfloat(stream), 4


def process_data(
    stream: BufferedReader, datatype: str | dict, max_length: int
) -> Tuple[Any, int]:
    processed = 0
     
    if isinstance(datatype, dict):
        data = []
        for _ in range(datatype["size"]):
            inner_data = {}
            for key, value in datatype["schema"].items():
                inner_value, data_processed = process_data(
                    stream, value, max_length - processed
                )
                inner_data[key] = inner_value
                processed += data_processed
            data.append(inner_data)
    elif datatype.startswith("data"):
        if len(datatype) <= 4:
            hex_text = stream.read(max_length - processed).hex()
        else:
            length = int(datatype[4:])
            hex_text = stream.read(length).hex()
            processed += length
        hex_text = " ".join(
            hex_text[j : j + 2] for j in range(0, len(hex_text), 2)
        ).upper()
        data = hex_text
    elif datatype.endswith(("byte", "short", "int", "long", "float")):
        if datatype.startswith("u"):
            data, data_processed = process_number(stream, datatype[1:], True)
        else:
            data, data_processed = process_number(stream, datatype, False)
        processed += data_processed
    elif datatype.startswith("toffset"):
        if datatype == "toffset":
            data = readtextoffset(stream, readint(stream, 8))
        else:
            data = readtextoffset(stream, readint(stream, 8), encoding=datatype[7:])
        processed += 8
    elif datatype.endswith("array"):
        offset = readint(stream, 8)
        count = readint(stream, 4)
        
        number_of_scena_flags_packed_together = int(datatype[0:-5])
        data = [] 
        for i_pack_u16 in range(0, count):
            print(hex(stream.tell()))
            for i_u16 in range(0, number_of_scena_flags_packed_together):
                data.append(readintoffset(stream, offset + i_pack_u16 * number_of_scena_flags_packed_together * 2 + i_u16 * 2, 2))
        processed += (8 + 4)
    else:
        raise Exception(f"Unknown data type {datatype}")

    return (data, processed)
