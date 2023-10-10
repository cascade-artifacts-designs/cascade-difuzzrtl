import os
import multiprocessing as mp

NUM_CORES = 240
DO_BOOM = False

elf2hex = 'riscv64-unknown-elf-elf2hex'
elf2hex_args = [ elf2hex, '--bit-width', '64', '--input' ]

# Should be called by the Docker container because we need elf2hex

PATH_TO_SRC_ELFS_DIR_ROCKET = 'difuzz-rtl/cascade-elfs/RocketTile'
PATH_TO_SRC_ELFS_DIR_BOOM = 'difuzz-rtl/cascade-elfs/BoomTile'

PATH_TO_DST_HEXS_DIR_ROCKET = 'difuzz-rtl/cascade-elfs/RocketTile/hex'
PATH_TO_DST_HEXS_DIR_BOOM = 'difuzz-rtl/cascade-elfs/BoomTile/hex'

# Make the destination directories if they don't exist
if not os.path.exists(PATH_TO_DST_HEXS_DIR_ROCKET):
    os.makedirs(PATH_TO_DST_HEXS_DIR_ROCKET, exist_ok=True)
if not os.path.exists(PATH_TO_DST_HEXS_DIR_BOOM):
    os.makedirs(PATH_TO_DST_HEXS_DIR_BOOM, exist_ok=True)

# Find all the elfs in the source directories
rocket_elfs = []
boom_elfs = []
for filename in os.listdir(PATH_TO_SRC_ELFS_DIR_ROCKET):
    # Dont take the 'hex' dir :D
    if filename.startswith('rocket'):
        rocket_elfs.append(filename)
if DO_BOOM:
    for filename in os.listdir(PATH_TO_SRC_ELFS_DIR_BOOM):
        # Dont take the 'hex' dir :D
        if filename.startswith('boom'):
            boom_elfs.append(filename)

# Copy the rocket and boom elfs to the destination directory
workloads = []
for filename in rocket_elfs:
    # Replace the extension in filename from elf to hex
    src_path = os.path.join(PATH_TO_SRC_ELFS_DIR_ROCKET, filename)
    hex_filename = filename.replace('.elf', '.hex')
    dst_path = os.path.join(PATH_TO_DST_HEXS_DIR_ROCKET, hex_filename)
    curr_elf2hex_args = elf2hex_args + [ src_path, '--output', dst_path]
    workloads.append(curr_elf2hex_args)
if DO_BOOM:
    for filename in boom_elfs:
        # Replace the extension in filename from elf to hex
        src_path = os.path.join(PATH_TO_SRC_ELFS_DIR_BOOM, filename)
        hex_filename = filename.replace('.elf', '.hex')
        dst_path = os.path.join(PATH_TO_DST_HEXS_DIR_BOOM, hex_filename)
        curr_elf2hex_args = elf2hex_args + [ src_path, '--output', dst_path]
        workloads.append(curr_elf2hex_args)

def hex_worker(workload):
    os.system(' '.join(workload))
    print('Done producing hex for {}'.format(workload[-1]))

with mp.Pool(NUM_CORES) as pool:
    pool.map(hex_worker, workloads)

