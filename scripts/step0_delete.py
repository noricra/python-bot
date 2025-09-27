import re
from pathlib import Path

SRC = Path('/workspace/bot_mlt.py')
BACKUP = Path('/workspace/bot_mlt.before_step0.py')

# Raw ranges string provided by user, including comments
RANGES_RAW = (
    "80, 85-86, 107-109, 127-128, 138-150, 185-195, 220, 275-277, 285-286, 288-289, 291-292, "
    "294-295, 297-300, 318-320, 347-349, 381-383, 405-407, 435-437, 456-458, 466-467, 469-470, "
    "472-473, 475-476, 478-481, 496-498, 512-514, 537-539, 569-578, 601, 607, 623-626, 652-661, "
    "670-683, 703-706, 716-721, 725-730, 737-738, 742-746, 751-769, 773-809, 923, 925, 952, 954-955, "
    "957-958, 969-971, 973-975, 981-982, 984-986, 998, 1004, 1010, 1014, 1060-1064, 1072-1091, "
    "1111-1114, 1116, 1126-1129, 1162-1163, 1180-1183, 1263-1266, 1312-1314, 1323-1333, 1344-1346, "
    "1391-1393, 1400-1402, 1420-1422, 1429-1444, 1469-1478, 1482-1484, 1494-1528, 1535-1547, 1558-1614, "
    "1622-1701, 1708-1855, 1867-1983, 1990-2006, 2041-2045, 2047-2055, 2069-2071, 2085-2088, 2124-2125, "
    "2134-2139, 2165-2170, 2185-2188, 2191-2197, 2242-2247, 2250-2261, 2268-2269, 2282-2285, 2312-2381, "
    "2403, 2407, 2423-2424, 2450-2465, 2470, 2482-2486, 2489, 2491, 2493, 2508-2539, 2554-2591, 2604-2605, "
    "2634-2635, 2647-2648, 2671-2672, 2705-2717, 2765-2768, 2792, 2802-2803, 2838, 2842-2872, 2875-2889, "
    "2892-2894, 2897-2906, 2926-2928, 2943-2945, 2948-2966, 2969-2983, 2986-2997, 3008-3009, 3024-3026, "
    "3103-3104, 3124-3133, 3196-3199, 3207-3214, 3238-3239, 3253-3256, 3265-3266, 3275-3277, 3283-3285, "
    "3292-3293, 3299-3302, 3319-3321, 3345-3347, 3356-3360, 3368-3369, 3372-3376, 3391-3393, 3404-3405, "
    "3412, 3428-3431, 3436-3447, 3464, 3487-3490, 3523, 3547-3550, 3612, 3646, 3677-3680, 3685-3693, 3710, "
    "3747-3750, 3796-3802, 3807-3813, 3817-3820, 3826-3834, 3839-3840, 3844-3852, 3874-3880, 3884-3885, "
    "3895-3904, 3951-3964, 3980-3981, 4012-4017, 4038-4048, 4071, 4086-4089, 4092-4093, 4112-4114, 4118-4120, "
    "4125-4126, 4135-4136, 4139-4141, 4156-4159, 4162-4163, 4179-4216, 4231-4234, 4240-4243, 4250-4251, 4254-4255, "
    "4278-4281, 4304, 4307-4318, 4322, 4337, 4340-4342, 4345-4348, 4352, 4367-4369, 4372-4375, 4379, 4394-4398, "
    "4404-4417, 4421-4460, 4463"
)


def parse_ranges(raw: str) -> set[int]:
    # Keep digits, dashes and commas; replace others by spaces
    cleaned = re.sub(r"[^0-9,\-]", " ", raw)
    parts = [p.strip() for p in cleaned.split(',') if p.strip()]
    lines: set[int] = set()
    for part in parts:
        if '-' in part:
            try:
                a, b = part.split('-', 1)
                start = int(a)
                end = int(b)
                if start <= end:
                    lines.update(range(start, end + 1))
            except Exception:
                continue
        else:
            try:
                lines.add(int(part))
            except Exception:
                continue
    return lines


def find_method_block(lines: list[str], method_name: str) -> tuple[int, int] | None:
    start_idx = None
    base_indent = None
    for i, s in enumerate(lines, start=1):
        st = s.lstrip(' ')
        if st.startswith(f"async def {method_name}("):
            start_idx = i
            base_indent = len(s) - len(st)
            break
    if start_idx is None:
        return None
    # Find end: next def/async def/class with same indent or less
    for j in range(start_idx + 1, len(lines) + 1):
        s = lines[j - 1]
        st = s.lstrip(' ')
        indent = len(s) - len(st)
        if indent == base_indent and (st.startswith('async def ') or st.startswith('def ') or st.startswith('class ')):
            return (start_idx, j - 1)
    return (start_idx, len(lines))


def main():
    src_text = SRC.read_text(encoding='utf-8')
    lines = src_text.splitlines()
    BACKUP.write_text(src_text, encoding='utf-8')

    # Compute preserve ranges for purchase flow methods
    preserve_blocks = []
    for name in ['buy_product_prompt', 'show_crypto_options', 'process_payment', 'check_payment_handler']:
        blk = find_method_block(lines, name)
        if blk:
            preserve_blocks.append(blk)

    def in_preserve(idx: int) -> bool:
        for a, b in preserve_blocks:
            if a <= idx <= b:
                return True
        return False

    to_delete = parse_ranges(RANGES_RAW)
    # Filter out preserved blocks
    filtered_delete = {i for i in to_delete if not in_preserve(i)}

    out_lines: list[str] = []
    for i, s in enumerate(lines, start=1):
        if i in filtered_delete:
            if s.lstrip().startswith('except'):
                out_lines.append(s)
            else:
                # drop line
                continue
        else:
            out_lines.append(s)

    Path(str(SRC)).write_text("\n".join(out_lines) + "\n", encoding='utf-8')


if __name__ == '__main__':
    main()

